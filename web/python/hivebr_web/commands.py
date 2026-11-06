"""UI -> Python commands. Each handler mirrors what the desktop GUI does."""
from __future__ import annotations

import base64
import json
import os
import tempfile

import numpy as np

from . import host, serialize

# Slider ranges of the desktop GUI (gui.py), used to clamp set_param values.
PARAM_RANGES = {
    "max_speed": (0.2, 8.0), "max_omega": (0.1, 6.0), "max_steer": (0.1, 1.2),
    "grid_size": (0.1, 5.0), "noise_sigma": (0.0, 1.0), "servo_max_speed": (0.5, 30.0),
    "goal_tolerance": (0.0, 100.0),
}


def dispatch(sim, raw):
    """Run one command (JSON string or dict). Never raises."""
    try:
        msg = json.loads(raw) if isinstance(raw, (str, bytes)) else dict(raw)
        name = msg["cmd"]
    except Exception:
        host.notice("warn", f"Invalid command: {str(raw)[:80]}", "invalid_command", raw=str(raw)[:80])
        return
    handler = HANDLERS.get(name)
    if handler is None:
        host.notice("warn", f"Unknown command: {name}", "unknown_command", name=name)
        return
    try:
        handler(sim, msg)
    except Exception as exc:  # a bad command must never break the run
        host.notice("warn", f"Command '{name}' failed: {type(exc).__name__}: {exc}", "command_failed",
                    name=name, error=f"{type(exc).__name__}: {exc}")
    sim.mark_dirty()


def _robot(sim, msg, key="robot"):
    idx = msg.get(key)
    return sim.selected_robot_index if idx is None else int(idx)


def _check_robot(sim, i):
    if not 0 <= i < sim.num_robots:
        raise IndexError(f"robot {i} does not exist")
    return i


def _num(msg, key, default=None):
    v = msg.get(key, default)
    if v is None:
        raise ValueError(f"missing '{key}'")
    v = float(v)
    if not np.isfinite(v):
        raise ValueError(f"'{key}' must be finite")
    return v


# ------------------------------------------------------------ run state ----
def _start(sim, msg): sim.running_simulation = True
def _pause(sim, msg): sim.running_simulation = False
def _toggle(sim, msg): sim.running_simulation = not sim.running_simulation
def _stop(sim, msg): sim.running = False
def _refresh(sim, msg): sim.frames.force_full(); sim._post_scene()


def _step_once(sim, msg):
    if not sim.running_simulation:
        sim.physics_step()


def _reset(sim, msg):
    sim.running_simulation = False
    sim.reset()


def _set_speed(sim, msg):
    sim.speed = max(0.0, _num(msg, "factor"))
    sim._next_tick = None


def _select_robot(sim, msg): sim.select_robot(int(msg["index"]))


# ------------------------------------------------------------ waypoints ----
def _add_waypoint(sim, msg):
    i = _check_robot(sim, _robot(sim, msg))
    mgr = sim.waypoint_managers[i]
    pos = [_num(msg, "x"), _num(msg, "y")]
    theta = msg.get("theta")
    if theta is None and mgr.define_orientation:
        theta = 0.0
    mgr.add_waypoint(pos if theta is None else pos + [float(theta)])


def _clear_waypoints(sim, msg):
    if msg.get("robot") is None:
        for m in sim.waypoint_managers:
            m.clear()
    else:
        sim.waypoint_managers[_check_robot(sim, int(msg["robot"]))].clear()


def _remove_waypoint(sim, msg):
    mgr = sim.waypoint_managers[_check_robot(sim, _robot(sim, msg))]
    k = int(msg["index"])
    del mgr.waypoints[k]
    if k < mgr.current_index:
        mgr.current_index -= 1


# ------------------------------------------------------------ obstacles ----
def _sync_obstacles(sim):
    sim.config.setdefault("world", {})["obstacles"] = np.array(sim.world.obstacles).tolist()


def _add_obstacle(sim, msg):
    r = _num(msg, "r", sim.world.default_obstacle_radius)
    if r <= 0:
        raise ValueError("radius must be positive")
    sim.world.add_obstacle((_num(msg, "x"), _num(msg, "y")), radius=r)
    _sync_obstacles(sim)


def _remove_obstacle(sim, msg):
    del sim.world.obstacles[int(msg["index"])]
    _sync_obstacles(sim)


def _clear_obstacles(sim, msg): sim.world.clear_obstacles()
def _remove_recharge(sim, msg):
    del sim.world.recharge_places[int(msg["index"])]


def _add_recharge(sim, msg): sim.world.recharge_places.append(np.array([_num(msg, "x"), _num(msg, "y"), 0.0]))


# ---------------------------------------------------------------- robots ----
def _clear_path(sim, msg):
    if msg.get("robot") is None:
        for r in sim.robots:
            r.clear_path()
        sim.frames.bump_path()
    else:
        i = _check_robot(sim, int(msg["robot"]))
        sim.robots[i].clear_path()
        sim.frames.bump_path(i)


def _set_pose(sim, msg):
    i = _check_robot(sim, _robot(sim, msg))
    robot = sim.robots[i]
    x, y, th = _num(msg, "x"), _num(msg, "y"), _num(msg, "theta", robot.theta)
    if sim.sim_time == 0.0 and hasattr(robot, "set_initial_pose"):
        robot.set_initial_pose(x, y, th)  # not started yet: reset returns here too
    robot.x, robot.y, robot.theta = x, y, th
    robot.clear_path()
    sim.frames.bump_path(i)


def _set_param(sim, msg):
    """Same effects as GUI.process_slider_event."""
    name = msg["name"]
    if name not in PARAM_RANGES:
        raise ValueError(f"unknown parameter '{name}'")
    lo, hi = PARAM_RANGES[name]
    value = min(hi, max(lo, _num(msg, "value")))
    cfg = sim.config
    if name in ("max_speed", "max_omega", "max_steer", "servo_max_speed"):
        cfg["robot"][name] = value
        for robot in sim.robots:
            if hasattr(robot, name):
                setattr(robot, name, value)
    elif name == "grid_size":
        sim.world.grid_size = value
        cfg["world"]["grid_size"] = value
    elif name == "noise_sigma":
        noise = cfg.setdefault("noise", {})
        noise["sigma_v"] = noise["sigma_omega"] = value
        noise.setdefault("limit", 1.0)
        noise["enabled"] = value > 0.0
    else:
        sim.set_goal_tolerance(value)


def _toggle_lidar(sim, msg): sim.lidar.enabled = not sim.lidar.enabled


def _toggle_noise(sim, msg):
    noise = sim.config.setdefault("noise", {})
    noise["enabled"] = not noise.get("enabled", False)


def _toggle_theme(sim, msg): sim.toggle_theme()
def _toggle_times(sim, msg): sim.config["show_times"] = not sim.config.get("show_times", True)


# ------------------------------------------------------------------ maps ----
def _load_map(sim, msg):
    name = os.path.basename(str(msg.get("name") or "map.png"))
    if os.path.splitext(name)[1].lower() not in (".png", ".jpg", ".jpeg"):
        name += ".png"
    folder = os.path.join(tempfile.gettempdir(), "hivebr_maps")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    with open(path, "wb") as f:
        f.write(base64.b64decode(msg["b64"]))
    res = _num(msg, "resolution", 0.1)
    if res <= 0:
        raise ValueError("resolution must be positive")
    kind = str(msg.get("kind") or "occupancy").lower()
    if kind not in ("occupancy", "line"):
        raise ValueError("kind must be 'occupancy' or 'line'")
    try:
        if kind == "line":
            sim.world.load_line_map(path, res)
            sim.config.setdefault("world", {})["line_map_image"] = path
        else:
            sim.world.load_map(path, res)
            sim.grid_map = sim.world.grid_map
    except Exception as exc:
        host.notice("error", f"Could not load map: {exc}", "map_load_failed", error=exc)
        return
    host.notice("info", f"{'Line track' if kind == 'line' else 'Map'} loaded: {name} (res {res} m/px)",
                "line_track_loaded" if kind == "line" else "map_loaded", name=name, res=res)


def _clear_map(sim, msg):
    sim.world.grid_map = None
    sim.grid_map = None
    sim.world.line_map = None
    sim._track_gray = None


def _rasterize(sim, strokes):
    """Draw strokes on the track canvas (PIL stands in for the pygame surface)."""
    from PIL import Image, ImageDraw

    ed = sim.track_editor
    if sim._track_gray is None:
        sim._track_gray = Image.new("L", (ed.width_px, ed.height_px), 255)
        lm = getattr(sim.world, "line_map", None)
        if lm is not None:
            sim._track_gray = Image.fromarray(lm.to_gray(), "L").resize((ed.width_px, ed.height_px))
    draw = ImageDraw.Draw(sim._track_gray)
    for stroke in strokes:
        pts = [(float(p[0]), float(p[1])) for p in stroke]
        if not pts:
            continue
        ed.begin(*pts[0])
        for p in pts[1:]:
            ed.extend(*p)
        ed.end()
        px = [ed.world_to_canvas(*p) for p in pts]
        r = max(1, ed.line_px // 2)
        if len(px) > 1:
            draw.line(px, fill=0, width=ed.line_px)
        for c in (px[0], px[-1]) if len(px) > 1 else px:
            draw.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=0)
    return np.array(sim._track_gray, dtype=np.uint8)


def _track_apply(sim, msg):
    gray = _rasterize(sim, msg.get("strokes") or [])
    sim.track_editor._gray_array = lambda: gray
    sim.apply_track()  # same as the desktop "Apply Track" button
    path = sim.config.get("world", {}).get("drawn_line_map_image", "config/line_drawn.png")
    sim._track_gray.save(path)


def _track_clear(sim, msg):
    sim._track_gray = None
    sim.clear_track()


def _track_export(sim, msg):
    lm = getattr(sim.world, "line_map", None)
    if lm is None and sim._track_gray is None:
        host.notice("warn", "No track to export", "no_track_to_export")
        return
    from PIL import Image
    import io
    img = Image.fromarray(lm.to_gray(), "L") if lm is not None else sim._track_gray
    buf = io.BytesIO()
    img.save(buf, "PNG")
    _send_file("track.png", "image/png", buf.getvalue())


# ----------------------------------------------------------- files / log ----
def _send_file(name, mime, data):
    host.post("file", {"name": name, "mime": mime, "b64": base64.b64encode(data).decode("ascii")})


def _save_config(sim, msg):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "config.yaml")
        sim.save_config(path)
        with open(path, "rb") as f:
            _send_file("config.yaml", "text/yaml", f.read())


def _export_log(sim, msg):
    fmt = str(msg.get("format", "csv")).lower()
    if fmt not in ("csv", "pkl"):
        raise ValueError("format must be 'csv' or 'pkl'")
    if not sim.logger._has_data():
        host.notice("warn", "No logged data yet", "no_log_data")
        return
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, f"hivebr_log.{fmt}")
        sim.logger.export(path)
        with open(path, "rb") as f:
            _send_file(f"hivebr_log.{fmt}", "text/csv" if fmt == "csv" else "application/octet-stream", f.read())
        extra = os.path.join(tmp, "hivebr_log_collisions.csv")
        if os.path.exists(extra):
            with open(extra, "rb") as f:
                _send_file("hivebr_log_collisions.csv", "text/csv", f.read())


def _get_log(sim, msg):
    host.post("log_data", serialize.build_log_data(sim, bool(msg.get("open", False))))


def _reset_logger(sim, msg): sim.logger.reset()


HANDLERS = {
    "start": _start, "pause": _pause, "toggle": _toggle, "step_once": _step_once,
    "reset": _reset, "stop": _stop, "set_speed": _set_speed, "select_robot": _select_robot,
    "add_waypoint": _add_waypoint, "clear_waypoints": _clear_waypoints, "remove_waypoint": _remove_waypoint,
    "add_obstacle": _add_obstacle, "remove_obstacle": _remove_obstacle, "clear_obstacles": _clear_obstacles,
    "add_recharge": _add_recharge, "remove_recharge": _remove_recharge, "clear_path": _clear_path, "set_pose": _set_pose,
    "set_param": _set_param, "toggle_lidar": _toggle_lidar, "toggle_noise": _toggle_noise,
    "toggle_theme": _toggle_theme, "toggle_times": _toggle_times,
    "load_map": _load_map, "clear_map": _clear_map,
    "track_apply": _track_apply, "track_clear": _track_clear, "track_export": _track_export,
    "save_config": _save_config, "export_log": _export_log, "get_log": _get_log,
    "reset_logger": _reset_logger, "refresh": _refresh,
}
