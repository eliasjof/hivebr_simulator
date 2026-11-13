"""Builders for the JSON messages sent to the UI (scene, frame, log_data).

Only plain Python values are produced: floats are rounded to 4 decimals and
NaN/inf become ``None``, so the result always survives ``allow_nan=False``.
"""
from __future__ import annotations

import base64
import io
import math

import numpy as np

MAX_LOG_POINTS = 6000
MAX_LIDAR_POINTS = 360

_TYPE_BY_CLASS = (
    ("HexagonalHolonomicLineFollower", "hexagonal_holonomic_line_follower"),
    ("HexagonalHolonomicRobot", "hexagonal_holonomic"),
    ("LineFollowerRobot", "line_follower"),
    ("DifferentialRobotFirstOrder", "differential_firstorder"),
    ("DifferentialRobot", "differential"),
    ("AckermannRobot", "ackermann"),
    ("BoatRobot", "boat"),
    ("HolonomicRobot", "holonomic"),
)


def f4(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return round(v, 4) if math.isfinite(v) else None


def pt(p):
    return [f4(p[0]), f4(p[1])]


def wp_list(wp):
    """[x, y] or [x, y, theta] when the waypoint carries a finite orientation."""
    out = pt(wp)
    if len(wp) > 2:
        th = f4(wp[2])
        if th is not None:
            out.append(th)
    return out


def png_b64(arr) -> str | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    img = Image.fromarray(np.ascontiguousarray(arr, dtype=np.uint8), "L")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def robot_type(robot) -> str:
    names = {c.__name__ for c in type(robot).__mro__}
    for cls, name in _TYPE_BY_CLASS:
        if cls in names:
            return name
    try:
        return str(robot.state().get("type", "differential"))
    except Exception:
        return "differential"


def robot_color(robot):
    colors = getattr(robot, "colors", None) or getattr(robot, "config", {}).get("colors", {})
    return [int(c) for c in colors.get("robot", (30, 144, 255))[:3]]


def _cfg_robot(robot):
    return getattr(robot, "config", {}).get("robot", {})


# ---------------------------------------------------------------- scene ----
def map_info(world):
    gm = world.grid_map
    if gm is None:
        return None
    raw = np.flipud(gm.grid)
    inflated = np.flipud(gm.inflated_grid)
    return {
        "kind": "occupancy",
        "png_b64": png_b64(np.where(raw, 0, 255)),
        "inflated_png_b64": None if np.array_equal(raw, inflated) else png_b64(np.where(inflated, 0, 255)),
        "show_inflation": bool(getattr(world, "show_inflation", True)),
        "width_m": f4(gm.width_m), "height_m": f4(gm.height_m), "resolution": f4(gm.resolution),
    }


def line_map_info(world):
    lm = getattr(world, "line_map", None)
    if lm is None:
        return None
    return {
        "png_b64": png_b64(lm.to_gray()),
        "width_m": f4(lm.width_m), "height_m": f4(lm.height_m), "resolution": f4(lm.resolution),
    }


def robot_info(index, robot):
    cfg = _cfg_robot(robot)
    rtype = robot_type(robot)
    # A plain hexagonal robot has no rectangular body. Its config may still
    # carry unrelated length/width keys (e.g. default.yaml); those must not
    # resize the hexagon, which uses radius as its circumradius.
    length = getattr(robot, "length", getattr(robot, "body_length", None))
    width = getattr(robot, "width", getattr(robot, "body_width", None))
    if length is None and not rtype.startswith("hexagonal"):
        length = cfg.get("length")
    if width is None and not rtype.startswith("hexagonal"):
        width = cfg.get("width")
    return {
        "id": index,
        "type": rtype,
        "radius": f4(getattr(robot, "radius", 0.1)),
        "length": f4(length),
        "width": f4(width),
        "wheel_base": f4(getattr(robot, "wheel_base", cfg.get("wheel_base"))),
        "color": robot_color(robot),
        "max_speed": f4(getattr(robot, "max_speed", None)),
        "max_omega": f4(getattr(robot, "max_omega", None)),
        "max_steer": f4(getattr(robot, "max_steer", None)),
        "num_sensors": getattr(robot, "num_sensors", None),
    }


def build_scene(sim, version, autostart):
    cfg, world, lidar = sim.config, sim.world, sim.lidar
    noise, inter, rcfg = cfg.get("noise", {}), cfg.get("interaction", {}), cfg.get("robot", {})
    wm = sim.waypoint_managers[0]
    return {
        "version": version,
        "instance": getattr(sim, "instance", None),
        "title": str(cfg.get("window", {}).get("title", "hiveBr")),
        "world": {"width": f4(world.width), "height": f4(world.height), "grid_size": f4(world.grid_size),
                  "show_origin": bool(world.show_origin), "show_axes": bool(world.show_axes)},
        "colors": _plain(cfg.get("colors", {})),
        "theme": str(cfg.get("theme", "dark")),
        "robots": [robot_info(i, r) for i, r in enumerate(sim.robots)],
        "map": map_info(world),
        "lineMap": line_map_info(world),
        "lidar": {"enabled": bool(lidar.enabled), "num_rays": int(lidar.num_rays),
                  "range": f4(lidar.range), "fov_deg": f4(math.degrees(lidar.fov))},
        "noise": {"enabled": bool(noise.get("enabled", False)),
                  "sigma_v": f4(noise.get("sigma_v", 0.0)), "sigma_omega": f4(noise.get("sigma_omega", 0.0))},
        "interaction": {"collision_policy": str(inter.get("collision_policy", "stop")),
                        "robot_collision": bool(inter.get("robot_collision", True)),
                        "comm_radius": f4(inter.get("comm_radius")),
                        "show_robot_links": bool(inter.get("show_robot_links", False))},
        "waypoints_cfg": {"goal_tolerance": f4(wm.goal_tolerance),
                          "define_orientation": bool(wm.define_orientation),
                          "show_tolerance_circle": bool(wm.show_tolerance_circle)},
        "params": {"max_speed": f4(rcfg.get("max_speed")), "max_omega": f4(rcfg.get("max_omega")),
                   "max_steer": f4(rcfg.get("max_steer")), "grid_size": f4(world.grid_size),
                   "noise_sigma": f4(noise.get("sigma_v", 0.0)),
                   "servo_max_speed": f4(rcfg.get("servo_max_speed", 6.28))},
        "autostart": bool(autostart),
    }


def static_signature(sim):
    """Cheap fingerprint of everything that goes into the scene message."""
    cfg, w, l = sim.config, sim.world, sim.lidar
    n, i, r = cfg.get("noise", {}), cfg.get("interaction", {}), cfg.get("robot", {})
    wm = sim.waypoint_managers[0]
    robots = tuple((type(b).__name__, b.radius, getattr(b, "max_speed", None), getattr(b, "max_omega", None),
                    getattr(b, "max_steer", None)) for b in sim.robots)
    return (
        w.width, w.height, w.grid_size, w.show_origin, w.show_axes, w.show_inflation,
        id(w.grid_map), id(getattr(w, "line_map", None)), cfg.get("theme"), id(cfg.get("colors")),
        l.enabled, l.num_rays, l.range, l.fov,
        n.get("enabled"), n.get("sigma_v"), n.get("sigma_omega"),
        i.get("collision_policy"), i.get("robot_collision"), i.get("comm_radius"), i.get("show_robot_links"),
        wm.goal_tolerance, wm.define_orientation, wm.show_tolerance_circle,
        r.get("servo_max_speed"), cfg.get("window", {}).get("title"), robots,
    )


def _plain(obj):
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [_plain(v) for v in obj]
    if isinstance(obj, (bool, str)) or obj is None:
        return obj
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        return f4(obj)
    return str(obj)


# ---------------------------------------------------------------- frame ----
def _velocity(robot):
    """(v, omega) in a form comparable across robot types."""
    if hasattr(robot, "speed") and hasattr(robot, "steer"):  # ackermann: yaw rate from bicycle model
        wb = getattr(robot, "wheel_base", 0.5) or 0.5
        return robot.speed, robot.speed / wb * math.tan(robot.steer)
    if hasattr(robot, "v"):
        return robot.v, getattr(robot, "omega", 0.0)
    if hasattr(robot, "vx"):
        return math.hypot(robot.vx, getattr(robot, "vy", 0.0)), 0.0
    return 0.0, 0.0


def robot_extra(robot, rtype):
    ex = {}
    if hasattr(robot, "steer"):
        ex["steer"] = f4(robot.steer)
    if hasattr(robot, "omega1"):
        ex["wheel_speeds"] = [f4(robot.omega1), f4(robot.omega2), f4(robot.omega3)]
    elif rtype in ("differential", "differential_firstorder", "line_follower"):
        half = 0.5 * float(_cfg_robot(robot).get("wheel_base", 0.285))
        ex["wheel_speeds"] = [f4(robot.v - robot.omega * half), f4(robot.v + robot.omega * half)]
    if hasattr(robot, "vx") and hasattr(robot, "vy"):
        ex["vx"], ex["vy"] = f4(robot.vx), f4(robot.vy)
    if hasattr(robot, "v_ref"):
        ex["v_ref"] = f4(robot.v_ref)
    if hasattr(robot, "sensor_local") and hasattr(robot, "sensor_world_position"):
        thr = getattr(robot, "line_threshold", 0.5)
        readings = getattr(robot, "sensor_readings", ())
        sensors = []
        for k in range(len(robot.sensor_local)):
            p = robot.sensor_world_position(k)
            val = float(readings[k]) if k < len(readings) else 0.0
            sensors.append({"x": f4(p[0]), "y": f4(p[1]), "value": f4(val), "on": bool(val > thr)})
        ex["sensors"] = sensors
        ex["line_error"] = f4(getattr(robot, "line_error", 0.0))
        ex["line_lost"] = bool(getattr(robot, "line_lost", False))
    if hasattr(robot, "lap_times"):
        laps = [f4(t) for t in robot.lap_times]
        finished = bool(getattr(robot, "finished", False))
        ex.update({
            "lap_count": len(laps), "lap_times": laps,
            "best_lap": min(laps) if laps else None,
            "finished": finished, "finish_time": f4(getattr(robot, "finish_time", None)),
            "time": f4(getattr(robot, "time", 0.0)),
            "current_lap": f4(robot.finish_time if finished else robot.time - robot.lap_start_time),
        })
    return ex


class FrameBuilder:
    """Builds frame messages and keeps the change-tracking state between them."""

    def __init__(self):
        self.wp_sig = self.obs_sig = None
        self.wp_version = self.obs_version = 0
        self.path_len = {}
        self.epoch = {}
        self.types = {}
        self._sent_wp = self._sent_obs = None
        self.full = True

    def force_full(self):
        self.full = True

    def bump_path(self, index=None):
        for i in (self.epoch if index is None else [index]):
            self.epoch[i] = self.epoch.get(i, 0) + 1
            self.path_len[i] = 0

    def _robot(self, sim, i, robot):
        n = len(robot.path)
        if n < self.path_len.get(i, 0):
            self.epoch[i] = self.epoch.get(i, 0) + 1
        self.path_len[i] = n
        self.epoch.setdefault(i, 0)

        if i not in self.types or self.types[i][0] is not type(robot):
            self.types[i] = (type(robot), robot_type(robot))
        v, omega = _velocity(robot)
        goal = sim.waypoint_managers[i]
        g = goal.get_current_waypoint()
        lidar = None
        if sim.lidar.enabled:
            readings = sim.robot_lidar_readings[i]
            stride = max(1, math.ceil(len(readings) / MAX_LIDAR_POINTS))
            lidar = [pt(r[2]) for r in readings[::stride]]
        return {
            "id": i, "x": f4(robot.x), "y": f4(robot.y), "theta": f4(robot.theta),
            "v": f4(v), "omega": f4(omega),
            "battery": f4(getattr(robot, "battery_percent", 100.0)),
            "battery_enabled": bool(getattr(robot, "enable_battery", False)),
            "charging": bool(getattr(robot, "is_charging", False)),
            "collision": bool(sim.collisions[i]),
            "path_epoch": self.epoch[i],
            "goal": None if g is None else wp_list(g),
            "wp_index": int(goal.current_index), "wp_total": len(goal.waypoints),
            "lidar": lidar,
            "extra": robot_extra(robot, self.types[i][1]),
        }

    def build(self, sim, *, running, speed, realtime, step, overlay=None):
        world = sim.world
        frame = {
            "t": f4(sim.sim_time), "step": int(step), "running": bool(running),
            "selected": int(sim.selected_robot_index), "speed": f4(speed), "realtime_factor": f4(realtime),
            "robots": [self._robot(sim, i, r) for i, r in enumerate(sim.robots)],
        }
        wp_sig = tuple(tuple(np.asarray(w, dtype=float).tobytes() for w in m.waypoints)
                       for m in sim.waypoint_managers)
        if wp_sig != self.wp_sig:
            self.wp_sig = wp_sig
            self.wp_version += 1
        frame["wp_version"] = self.wp_version
        if self.full or frame["wp_version"] != self._sent_wp:
            frame["waypoints"] = [[wp_list(w) for w in m.waypoints] for m in sim.waypoint_managers]
            self._sent_wp = self.wp_version

        recharge = [(float(p[0]), float(p[1])) for p in world.recharge_places]
        obs_sig = (np.asarray(world.obstacles, dtype=float).tobytes(), tuple(recharge))
        if obs_sig != self.obs_sig:
            self.obs_sig = obs_sig
            self.obs_version += 1
        frame["obstacles_version"] = self.obs_version
        if self.full or self.obs_version != self._sent_obs:
            frame["obstacles"] = [[f4(o[0]), f4(o[1]), f4(o[2])] for o in world.obstacles]
            frame["recharge"] = [pt(p) for p in recharge]
            self._sent_obs = self.obs_version

        inter = sim.config.get("interaction", {})
        if inter.get("show_robot_links", False) and sim.num_robots > 1:
            from hivebr.engine import interaction
            nb = interaction.build_neighbors(sim.robots, inter.get("comm_radius"))
            frame["links"] = [[i, j] for i, js in nb.items() for j in sorted(js) if j > i]
        if overlay:
            frame["overlay"] = overlay
        frame["collisions_total"] = len(sim.collision_events)
        self.full = False
        return frame


# ------------------------------------------------------------------ log ----
def _wrap(a):
    return (a + np.pi) % (2.0 * np.pi) - np.pi


def _col(frames, attr):
    return np.array([np.nan if (v := getattr(f, attr, None)) is None else v for f in frames], dtype=float)


def _vlist(arr, idx):
    if arr is None or not np.any(np.isfinite(arr)):
        return []
    return [f4(v) for v in arr[idx]]


def _log_signals(rtype, frames, t, theta, robot):
    """(v, omega, v_cmd, omega_cmd) arrays; any may be None when unavailable."""
    if rtype == "holonomic":
        v = np.hypot(_col(frames, "vx_real"), _col(frames, "vy_real"))
        vc = np.hypot(_col(frames, "vx"), _col(frames, "vy"))
        return v, _angular_rate(t, theta), vc, None
    if rtype == "ackermann":
        wb = float(getattr(robot, "wheel_base", 0.5) or 0.5)
        sp, spc = _col(frames, "speed_real"), _col(frames, "speed")
        st, stc = _col(frames, "steer_real"), _col(frames, "steer")
        return sp, sp / wb * np.tan(st), spc, spc / wb * np.tan(stc)
    if rtype in ("differential", "boat", "differential_firstorder"):
        vc = _col(frames, "v_ref" if rtype == "differential_firstorder" else "v")
        return _col(frames, "v_real"), _col(frames, "omega_real"), vc, _col(frames, "omega")
    return None, None, None, None


def _angular_rate(t, theta):
    if len(t) < 2:
        return None
    dt = np.diff(t)
    dt[dt == 0] = np.nan
    rate = _wrap(np.diff(theta)) / dt
    return np.concatenate([rate[:1], rate])


def build_log_data(sim, open_window=False, multi=None):
    """``multi`` is a MultiRobotLog; defaults to the simulator's own logger."""
    from hivebr.engine.data_logger import format_collision_event

    if multi is None:
        multi = sim.logger.result()
    robots = []
    for index, log in multi.logs.items():
        frames = log.frames
        if not frames:
            continue
        stride = max(1, math.ceil(len(frames) / MAX_LOG_POINTS))
        t, x, y, th = (_col(frames, a) for a in ("t", "x", "y", "theta"))
        robot = sim.robots[index] if sim is not None and index < len(sim.robots) else None
        v, om, vc, omc = _log_signals(log.robot_type, frames, t, th, robot)
        if v is None:  # no logged velocities for this type: differentiate the pose
            dt = np.diff(t)
            dt[dt == 0] = np.nan
            v = np.concatenate([[np.nan], np.hypot(np.diff(x), np.diff(y)) / dt])
            om = np.concatenate([[np.nan], _wrap(np.diff(th)) / dt])
        gx, gy, gth = (np.array([np.nan if f.goal is None or len(f.goal) <= k else f.goal[k] for f in frames])
                       for k in range(3))
        sel = slice(None, None, stride)
        entry = {
            "id": index, "type": robot_type(robot) if robot is not None else log.robot_type,
            "color": robot_color(robot) if robot is not None else [30, 144, 255],
            "t": _vlist(t, sel), "x": _vlist(x, sel), "y": _vlist(y, sel), "theta": _vlist(th, sel),
            "v": _vlist(v, sel), "omega": _vlist(om, sel),
            "v_cmd": _vlist(vc, sel), "omega_cmd": _vlist(omc, sel),
            "err_pos": _vlist(np.hypot(x - gx, y - gy), sel), "err_theta": _vlist(_wrap(th - gth), sel),
            "segments": [int(f.segment) for f in frames[sel]],
        }
        if log.robot_type == "ackermann":
            entry["steer"] = _vlist(_col(frames, "steer_real"), sel)
            entry["steer_cmd"] = _vlist(_col(frames, "steer"), sel)
        robots.append(entry)
    return {"open": bool(open_window), "robots": robots,
            "collisions": [format_collision_event(e) for e in multi.collision_events]}
