"""Headless Simulator for the browser.

``BrowserSimulator`` reuses the real engine (physics, LiDAR, waypoints,
collisions, logger) and replaces only the pygame/GUI layer: input comes from
host commands and output goes out as ``scene``/``frame`` messages.
"""
from __future__ import annotations

import traceback
from collections import deque

import pygame

import hivebr.engine as engine_pkg
import hivebr.engine.simulator as sim_mod
from hivebr.engine.camera import Camera2D

from . import commands, host, serialize

# Set by the runner before executing user code.
autostart = False

_Base = getattr(sim_mod.Simulator, "_browser_base", sim_mod.Simulator)
_current = None  # last simulator created; used by the log plot hook

FRAME_MS = 1000.0 / 60.0
FRAME_MS_UNPACED = 1000.0 / 30.0
IDLE_SLEEP_MS = 33.0
MAX_OVERLAY_ITEMS = 5000


class _FloatCamera(Camera2D):
    """Camera that keeps sub-pixel precision so overlays map back to exact metres."""

    def world_to_screen(self, px, py):
        ox, oy = self._display_offsets()
        sx = (px - self.offset[0]) * self.scale + ox
        sy = self.viewport_height - ((py - self.offset[1]) * self.scale + oy)
        return float(sx), float(sy)


class NullGUI:
    """Replacement for ui.gui.GUI: no widgets, no windows."""

    def __init__(self, *args, **kwargs):
        self.elements = {}
        self.obstacle_radius_window = self.obstacle_radius_entry = None
        self.obstacle_radius_ok = self.obstacle_radius_cancel = None
        self.orientation_window = self.orientation_entry = None

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: None


class BrowserSimulator(_Base):
    _browser_base = _Base

    def __init__(self, *args, **kwargs):
        global _current
        super().__init__(*args, **kwargs)
        _current = self
        self.camera.__class__ = _FloatCamera
        self.speed = 1.0
        self.frames = serialize.FrameBuilder()
        self.step_count = 0
        self.scene_version = 0
        self._sig = None
        self._dirty = True
        self._last_emit = -1e9
        self._next_tick = None
        self._rt = deque()
        self._overlay_disabled = False
        self._autostart_pending = bool(autostart)
        self._track_gray = None
        if autostart:
            self.running_simulation = True
        self._post_scene()
        self._emit()

    # ---------------------------------------------------------- output ----
    def _post_scene(self):
        self.scene_version += 1
        self._sig = serialize.static_signature(self)
        self.frames.force_full()
        host.post("scene", serialize.build_scene(self, self.scene_version, autostart))

    def mark_dirty(self):
        self._dirty = True

    def _emit_if_due(self, now):
        if not self._dirty:
            return
        if now - self._last_emit >= (FRAME_MS if self.speed > 0 else FRAME_MS_UNPACED):
            self._emit(now)

    def _emit(self, now=None):
        if now is None:
            now = host.get_host().now()
        if serialize.static_signature(self) != self._sig:
            self._post_scene()
        running = bool(self.running_simulation and self.running)
        frame = self.frames.build(
            self, running=running, speed=self.speed, realtime=self._realtime(now, running),
            step=self.step_count, overlay=self._overlay())
        host.post("frame", frame)
        self._last_emit = now
        self._dirty = False

    def _realtime(self, now, running):
        """Simulated seconds per wall second over a ~1.5 s moving window."""
        if not running:
            self._rt.clear()
            return 0.0
        self._rt.append((now, self.sim_time))
        while len(self._rt) > 2 and now - self._rt[0][0] > 1500.0:
            self._rt.popleft()
        t0, s0 = self._rt[0]
        wall = (now - t0) / 1000.0
        return (self.sim_time - s0) / wall if wall > 1e-3 else 0.0

    def _overlay(self):
        """Run draw_callback once and return its recorded primitives in metres."""
        if self.draw_callback is None:
            return None
        if self._overlay_disabled:
            return []
        pygame._begin_record(self.screen)
        try:
            self.draw_callback(self, self.screen)
        except Exception as exc:
            self._overlay_disabled = True
            traceback.print_exc()
            host.notice("warn", f"draw_callback disabled after an error: {exc!r}", "draw_callback_disabled", error=repr(exc))
        finally:
            items = pygame._end_record()
        cam = self.camera
        scale = cam.scale
        out = []
        for kind, color, pts, size in items[:MAX_OVERLAY_ITEMS]:
            c = _rgb(color)
            world = [serialize.pt(cam.screen_to_world(x, y)) for x, y in pts]
            if kind == "line":
                out.extend({"k": "line", "p": [a, b], "c": c, "w": _px(size)} for a, b in zip(world, world[1:]))
            elif kind == "circle":
                radius, width = size
                out.append({"k": "circle", "p": world[0], "r": serialize.f4(radius / scale), "c": c, "w": _px(width)})
            else:
                out.append({"k": "poly", "p": world, "c": c, "w": _px(size)})
        return out

    # ----------------------------------------------------------- input ----
    def _drain(self, h):
        for _ in range(256):
            raw = h.poll()
            if raw is None:
                break
            commands.dispatch(self, raw)

    # ------------------------------------------------------------ loop ----
    def run(self):
        self._dirty = True
        self._emit()
        while self.running:
            self.step()
        self._finish()

    def _finish(self):
        self._dirty = True
        self._emit()

    def step(self):
        h = host.get_host()
        if self._autostart_pending:
            self._autostart_pending = False
            self.running_simulation = True
        self._drain(h)
        if not self.running:
            return self.dt
        if self.running_simulation:
            self._pace(h)
        if self.running and self.running_simulation:
            self.physics_step()
            if self.speed > 0:
                self._next_tick = (self._next_tick or h.now()) + self.dt * 1000.0 / self.speed
        else:
            self._next_tick = None
        now = h.now()
        self._emit_if_due(now)
        if self.running and not self.running_simulation:
            wait = IDLE_SLEEP_MS
            if self._dirty:
                wait = max(1.0, min(wait, FRAME_MS - (now - self._last_emit)))
            h.sleep(wait)
        return self.dt

    def _pace(self, h):
        """Sleep until the next physics tick is due; wakes early on commands."""
        if self.speed <= 0:
            self._next_tick = None
            return
        while self.running and self.running_simulation:
            now = h.now()
            if self._next_tick is None or now - self._next_tick > 250.0:
                self._next_tick = now  # first tick, or fell behind: do not burst to catch up
            wait = self._next_tick - now
            if wait <= 0.2:
                return
            self._emit_if_due(now)
            h.sleep(wait)
            self._drain(h)

    def physics_step(self):
        """One physics tick, regardless of the running flag (used by step_once)."""
        prev = self.running_simulation
        self.running_simulation = True
        try:
            self.update_simulation()
            self.logger.draw_callback(self, self.screen)
        finally:
            self.running_simulation = prev
        self.step_count += 1
        self._dirty = True

    def reset(self):
        super().reset()
        self.step_count = 0
        self._next_tick = None
        self.frames.bump_path()
        self._dirty = True

    # ----------------------------------------- display/GUI no-ops ----------
    def resize(self, new_width, new_height): pass
    def draw(self, fps=0): pass
    def process_events(self): pass
    def handle_button_event(self, event): pass
    def cleanup_closed_windows(self): pass
    def confirm_obstacle_radius(self): pass
    def confirm_waypoint_orientation(self): pass
    def open_resolution_window(self): pass
    def is_modal_open(self): return False
    def _draw_explosion(self, robot): pass
    def _draw_robot_links(self): pass


def _rgb(color):
    try:
        return [max(0, min(255, int(v))) for v in list(color)[:3]]
    except (TypeError, ValueError):
        return [255, 255, 255]


def _px(width):
    try:
        return max(0, int(width))
    except (TypeError, ValueError):
        return 1


def _show_log_plot(multi_log, title=None):
    """Replaces the Tk plot window: sends the log to the UI instead."""
    if multi_log is None or not multi_log:
        print("[PlotWindow] No data to plot.")
        return
    host.post("log_data", serialize.build_log_data(_current, True, multi_log))


def install():
    """Swap the pygame-based engine pieces for their browser counterparts (idempotent)."""
    from hivebr.engine import plot_window

    sim_mod.Simulator = BrowserSimulator
    engine_pkg.Simulator = BrowserSimulator
    sim_mod.GUI = NullGUI
    sim_mod._render_honeybee_icon = lambda *a, **k: None
    plot_window.show_interactive_plot = _show_log_plot
