"""UI -> Python commands. Each handler mirrors what the desktop GUI does."""
from __future__ import annotations

import base64
import json
import math
import os
import shutil
import tempfile

import numpy as np
import yaml

from . import edits, host, serialize

# The client config lives inside the extracted /hivebr tree (CWD during a run).
CONFIG_PATH = os.path.join("config", "default.yaml")
# Pristine copy of the bundled default, written by the worker at boot.
CONFIG_DEFAULT_PATH = os.path.join("config", ".default.orig.yaml")

# Slider ranges of the desktop GUI (gui.py), used to clamp set_param values.
PARAM_RANGES = {
    "max_speed": (0.2, 8.0), "max_omega": (0.1, 6.0), "max_steer": (0.1, 1.2),
    "grid_size": (0.1, 5.0), "noise_sigma": (0.0, 1.0), "servo_max_speed": (0.5, 30.0),
    "goal_tolerance": (0.0, 100.0),
}


# Commands that change scene collections; their effect is recorded as a delta.
_COLLECTION_COMMANDS = {
    "add_waypoint", "clear_waypoints", "remove_waypoint",
    "add_obstacle", "remove_obstacle", "clear_obstacles",
    "add_recharge", "remove_recharge",
}
# Run controls only make sense while a script is executing.
_RUN_CONTROLS = {"start", "pause", "toggle", "stop", "step_once"}


def dispatch(sim, raw, editing=False):
    """Run one command (JSON string or dict). Never raises.

    ``editing`` is set when the command comes from the idle editor: run
    controls are ignored, because there is no execution loop to drive.
    """
    try:
        msg = json.loads(raw) if isinstance(raw, (str, bytes)) else dict(raw)
        name = msg["cmd"]
    except Exception:
        host.notice("warn", f"Invalid command: {str(raw)[:80]}", "invalid_command", raw=str(raw)[:80])
        return
    if editing and name in _RUN_CONTROLS:
        return
    handler = HANDLERS.get(name)
    if handler is None:
        host.notice("warn", f"Unknown command: {name}", "unknown_command", name=name)
        return
    try:
        before = edits.state().snapshot(sim) if name in _COLLECTION_COMMANDS else None
        result = handler(sim, msg)
    except Exception as exc:  # a bad command must never break the run
        host.notice("warn", f"Command '{name}' failed: {type(exc).__name__}: {exc}", "command_failed",
                    name=name, error=f"{type(exc).__name__}: {exc}")
    else:
        if before is not None:
            edits.state().record_collections(before, edits.state().snapshot(sim))
        _record_single(sim, name, msg, result)
    sim.mark_dirty()


def _record_single(sim, name, msg, result):
    """Record explicit (single-valued) choices made through the UI."""
    st = edits.state()
    if name == "set_pose":
        index = _robot(sim, msg)
        robot = sim.robots[index]
        st.record_pose(index, robot.x, robot.y, robot.theta)
    elif name == "set_param":
        _record_param(sim, msg.get("name"))
    elif name == "load_map" and result:
        st.record_map(result["kind"], result["path"], result["res"])
    elif name == "clear_map":
        st.record_clear_map()
    elif name == "track_apply" and result:
        st.record_track(result)
        # `apply_track` puts every robot on the track start; keep that choice.
        for index, robot in enumerate(sim.robots):
            st.record_pose(index, robot.x, robot.y, robot.theta)
    elif name == "track_clear":
        st.record_clear_track()


def _record_param(sim, name):
    if name in ("max_speed", "max_omega", "max_steer", "servo_max_speed"):
        value = sim.config.get("robot", {}).get(name)
    elif name == "grid_size":
        value = sim.world.grid_size
    elif name == "noise_sigma":
        value = sim.config.get("noise", {}).get("sigma_v")
    elif name == "goal_tolerance":
        value = sim.waypoint_managers[0].goal_tolerance
    else:
        return
    if value is not None:
        edits.state().record_param(name, value)



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
    """Keep the config in sync so a later `load_scene_from_config` sees them."""
    sim.config["obstacles"] = [
        {"x": float(o[0]), "y": float(o[1]), "radius": float(o[2])}
        for o in sim.world.obstacles
    ]
    sim.config.setdefault("world", {})["obstacles"] = [
        [float(o[0]), float(o[1]), float(o[2])] for o in sim.world.obstacles
    ]


def _add_obstacle(sim, msg):
    r = _num(msg, "r", sim.world.default_obstacle_radius)
    if r <= 0:
        raise ValueError("radius must be positive")
    sim.world.add_obstacle((_num(msg, "x"), _num(msg, "y")), radius=r)
    _sync_obstacles(sim)


def _remove_obstacle(sim, msg):
    del sim.world.obstacles[int(msg["index"])]
    _sync_obstacles(sim)


def _clear_obstacles(sim, msg):
    sim.world.clear_obstacles()
    _sync_obstacles(sim)

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
        world_cfg = sim.config.setdefault("world", {})
        if kind == "line":
            sim.world.load_line_map(path, res)
            world_cfg["line_map_image"] = path
        else:
            sim.world.load_map(path, res)
            sim.grid_map = sim.world.grid_map
            world_cfg["map_image"] = path
        world_cfg["resolution"] = res
    except Exception as exc:
        host.notice("error", f"Could not load map: {exc}", "map_load_failed", error=exc)
        return None
    host.notice("info", f"{'Line track' if kind == 'line' else 'Map'} loaded: {name} (res {res} m/px)",
                "line_track_loaded" if kind == "line" else "map_loaded", name=name, res=res)
    return {"kind": kind, "path": path, "res": res}


def _clear_map(sim, msg):
    sim.world.grid_map = None
    sim.grid_map = None
    sim.world.line_map = None
    sim._track_gray = None
    world_cfg = sim.config.setdefault("world", {})
    world_cfg.pop("map_image", None)
    world_cfg.pop("line_map_image", None)



def _rasterize(sim, strokes, fresh=False, default_width=0.02):
    """Draw strokes on the track canvas (PIL stands in for the pygame surface).

    ``fresh=True`` replaces the whole track with the drawn strokes instead of
    compositing them over the track that is currently applied.
    """
    from PIL import Image, ImageDraw

    ed = sim.track_editor
    if fresh or sim._track_gray is None:
        sim._track_gray = Image.new("L", (ed.width_px, ed.height_px), 255)
    draw = ImageDraw.Draw(sim._track_gray)
    first_pose = None
    first_stroke = None
    for stroke in strokes:
        # Support both formats: {points, width} and a plain list of points.
        if isinstance(stroke, dict) and "points" in stroke:
            pts = [(float(p[0]), float(p[1])) for p in stroke["points"]]
            line_width = float(stroke.get("width", default_width))
        else:
            pts = [(float(p[0]), float(p[1])) for p in stroke]
            line_width = float(default_width)
        if not pts:
            continue
        if first_pose is None and len(pts) >= 2:
            x0, y0 = pts[0]
            x1, y1 = pts[1]
            first_pose = (x0, y0, math.atan2(y1 - y0, x1 - x0))
            first_stroke = pts
        px = [ed.world_to_canvas(*p) for p in pts]
        # Convert line width from meters to pixels (resolution is m/px).
        line_px = max(1, int(round(line_width / ed.resolution)))
        r = max(1, line_px // 2)
        if len(px) > 1:
            draw.line(px, fill=0, width=line_px)
        for c in (px[0], px[-1]) if len(px) > 1 else px:
            draw.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=0)
    # Keep the pygame canvas in sync: TrackEditor.apply/save read from it.
    import pygame
    gray = np.array(sim._track_gray, dtype=np.uint8)
    rgb = np.ascontiguousarray(np.repeat(gray[:, :, None], 3, axis=2))
    ed.canvas = pygame.image.frombuffer(rgb.tobytes(), (ed.width_px, ed.height_px), "RGB")
    ed.stroke_world = first_stroke or []
    ed.start_pose = first_pose
    # The browser pygame stand-in has no pixels: make TrackEditor.build_line_map
    # read the raster we just drew instead of the blank canvas.
    ed._gray_array = lambda: np.array(sim._track_gray, dtype=np.uint8)
    return gray


def _track_apply(sim, msg):
    # Apply replaces the current track with the drawing (draw -> apply).
    strokes = msg.get("strokes") or []
    line_width = float(msg.get("line_width", 0.02))
    _rasterize(
        sim,
        strokes,
        fresh=True,
        default_width=line_width,
    )
    sim.apply_track()  # same as the desktop "Apply Track" button
    path = sim.config.get("world", {}).get("drawn_line_map_image", "config/line_drawn.png")
    sim._track_gray.save(path)
    return {"strokes": strokes, "line_width": line_width, "path": path}



def _track_clear(sim, msg):
    # Clear the drawing and the track that was generated from it.
    sim._track_gray = None
    ed = sim.track_editor
    if ed is not None and "_gray_array" in getattr(ed, "__dict__", {}):
        del ed._gray_array
    sim.clear_track()
    if getattr(sim.world, "line_map", None) is not None:
        sim.world.line_map = None
    world_cfg = sim.config.get("world", {})
    drawn_path = world_cfg.get("drawn_line_map_image", "config/line_drawn.png")
    if world_cfg.get("line_map_image") in (drawn_path, "config/line_drawn.png"):
        world_cfg["line_map_image"] = ""


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


def _post_client_config(path, reset=False):
    """Send the YAML bytes to the UI so it can persist (or forget) them."""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("ascii")
    host.post("client_config", {"path": os.path.abspath(path), "b64": data, "reset": bool(reset)})


def _update_config(sim, msg):
    """Write the current parameters to config/default.yaml inside the client FS."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    sim.save_config(CONFIG_PATH)
    _post_client_config(CONFIG_PATH)
    host.notice(
        "info",
        f"Config updated: {CONFIG_PATH}",
        "config_updated",
        path=CONFIG_PATH,
    )


def _default_params(cfg):
    """Parameter values from the pristine bundled config (the sliders of the GUI)."""
    robot = cfg.get("robot") or {}
    world = cfg.get("world") or {}
    noise = cfg.get("noise") or {}
    waypoints = cfg.get("waypoints") or {}
    params = {k: robot[k] for k in ("max_speed", "max_omega", "max_steer") if k in robot}
    params["servo_max_speed"] = robot.get("servo_max_speed", 6.28)
    if "grid_size" in world:
        params["grid_size"] = world["grid_size"]
    if "sigma_v" in noise:
        params["noise_sigma"] = noise["sigma_v"]
    elif "sigma_omega" in noise:
        params["noise_sigma"] = noise["sigma_omega"]
    if "goal_tolerance" in waypoints:
        params["goal_tolerance"] = waypoints["goal_tolerance"]
    return params


def _reset_config(sim, msg):
    """Restore config/default.yaml (and the window parameters) to the bundled defaults."""
    if not os.path.exists(CONFIG_DEFAULT_PATH):
        raise FileNotFoundError(f"original config not found: {CONFIG_DEFAULT_PATH}")
    with open(CONFIG_DEFAULT_PATH, encoding="utf-8") as f:
        defaults = yaml.safe_load(f) or {}
    shutil.copyfile(CONFIG_DEFAULT_PATH, CONFIG_PATH)
    for name, value in _default_params(defaults).items():
        _set_param(sim, {"name": name, "value": value})
    # set_param derives noise.enabled from sigma, so restore the toggles explicitly.
    lidar = defaults.get("lidar") or {}
    if "enabled" in lidar:
        sim.lidar.enabled = bool(lidar["enabled"])
    noise = defaults.get("noise") or {}
    if "enabled" in noise:
        sim.config.setdefault("noise", {})["enabled"] = bool(noise["enabled"])
    _post_client_config(CONFIG_PATH, reset=True)
    edits.state().params.clear()  # the restored values are the new baseline
    host.notice(
        "info",
        f"Config restored: {CONFIG_PATH}",
        "config_reset",
        path=CONFIG_PATH,
    )


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
    "save_config": _save_config, "update_config": _update_config, "reset_config": _reset_config,
    "export_log": _export_log, "get_log": _get_log,
    "reset_logger": _reset_logger, "refresh": _refresh,
}
