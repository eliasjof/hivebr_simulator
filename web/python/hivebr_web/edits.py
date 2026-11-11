"""User edits made outside a run, applied on top of every new simulator.

The web UI can edit the scene while no script is running. Those edits are kept
here as *deltas*: collections (obstacles, recharge points and waypoints) are
merged with whatever the script defines, while single-valued resources (map,
drawn track, robot poses and parameters) are explicit user choices that win over
the script.

The state lives in the worker for the whole browser session. Reloading the page
(or restarting the interpreter) starts from the bundled/default scene again.
"""
from __future__ import annotations

import math

import numpy as np


# ---------------------------------------------------------------- keys ----
def _round(value) -> float:
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return 0.0


def obstacle_key(obs) -> tuple:
    return (
        _round(obs[0]),
        _round(obs[1]),
        _round(obs[2]) if len(obs) > 2 else 0.0,
    )


def recharge_key(place) -> tuple:
    return (_round(place[0]), _round(place[1]))


def waypoint_key(wp) -> tuple:
    values = [_round(wp[0]), _round(wp[1])]
    if len(wp) > 2:
        theta = _theta(wp[2])
        if theta is not None:
            values.append(_round(theta))
    return tuple(values)


def _theta(value):
    try:
        theta = float(value)
    except (TypeError, ValueError):
        return None
    return theta if math.isfinite(theta) else None


def obstacle_value(obs) -> list:
    return [float(obs[0]), float(obs[1]), float(obs[2]) if len(obs) > 2 else 0.0]


def recharge_value(place) -> list:
    return [float(place[0]), float(place[1])]


def waypoint_value(wp) -> list:
    values = [float(wp[0]), float(wp[1])]
    if len(wp) > 2:
        theta = _theta(wp[2])
        if theta is not None:
            values.append(theta)
    return values


def _index(values, key) -> dict:
    """Map ``key -> value`` while keeping insertion order."""
    out = {}
    for value in values:
        out[key(value)] = value
    return out


# --------------------------------------------------------------- state ----
class EditState:
    """Cumulative user edits, relative to the scene the user has seen."""

    def __init__(self):
        self.obstacles_added = {}       # key -> [x, y, r]
        self.obstacles_removed = set()  # keys
        self.recharge_added = {}        # key -> [x, y]
        self.recharge_removed = set()
        self.waypoints_added = {}       # robot -> {key: [x, y(, theta)]}
        self.waypoints_removed = {}     # robot -> {key}
        self.map_set = False            # the user explicitly chose a map
        self.map = None                 # {"kind", "path", "res"}
        self.track_set = False          # the user explicitly chose a track
        self.track = None               # {"strokes", "line_width", "path"}
        self.poses = {}                 # robot -> [x, y, theta]
        self.params = {}                # name -> value

    # ---- recording -------------------------------------------------------
    def snapshot(self, sim) -> dict:
        return {
            "obstacles": _index(sim.world.obstacles, obstacle_key),
            "recharge": _index(sim.world.recharge_places, recharge_key),
            "waypoints": {
                i: _index(manager.waypoints, waypoint_key)
                for i, manager in enumerate(sim.waypoint_managers)
            },
        }

    def record_collections(self, before: dict, after: dict) -> None:
        _record_diff(
            self.obstacles_added, self.obstacles_removed,
            before.get("obstacles", {}), after.get("obstacles", {}), obstacle_value,
        )
        _record_diff(
            self.recharge_added, self.recharge_removed,
            before.get("recharge", {}), after.get("recharge", {}), recharge_value,
        )
        before_wp = before.get("waypoints", {})
        after_wp = after.get("waypoints", {})
        for robot in set(before_wp) | set(after_wp):
            added = self.waypoints_added.setdefault(robot, {})
            removed = self.waypoints_removed.setdefault(robot, set())
            _record_diff(
                added, removed,
                before_wp.get(robot, {}), after_wp.get(robot, {}), waypoint_value,
            )

    def record_map(self, kind: str, path: str, resolution: float) -> None:
        self.map_set = True
        self.map = {"kind": kind, "path": path, "res": float(resolution)}
        if kind == "line":
            # A line map replaces the track that was drawn before it.
            self.track_set = True
            self.track = None

    def record_clear_map(self) -> None:
        self.map_set = True
        self.map = None
        self.track_set = True
        self.track = None

    def record_track(self, track: dict) -> None:
        self.track_set = True
        self.track = track
        if self.map and self.map.get("kind") == "line":
            self.map = None

    def record_clear_track(self) -> None:
        self.track_set = True
        self.track = None
        if self.map and self.map.get("kind") == "line":
            self.map_set = True
            self.map = None

    def record_pose(self, robot: int, x: float, y: float, theta: float) -> None:
        self.poses[int(robot)] = [float(x), float(y), float(theta)]

    def record_param(self, name: str, value: float) -> None:
        self.params[str(name)] = float(value)


def _record_diff(added: dict, removed: set, before: dict, after: dict, value) -> None:
    for key, item in after.items():
        if key not in before:
            added[key] = value(item)
            removed.discard(key)
    for key, item in before.items():
        if key not in after:
            if key in added:
                added.pop(key, None)
            else:
                removed.add(key)


_STATE = EditState()


def state() -> EditState:
    return _STATE


def reset() -> None:
    """Forget every edit (used by tests and by a full interpreter restart)."""
    global _STATE
    _STATE = EditState()


# -------------------------------------------------------------- apply ----
def apply(sim) -> None:
    """Apply the recorded deltas to a freshly created simulator."""
    st = _STATE
    _apply_obstacles(sim, st)
    _apply_recharge(sim, st)
    _apply_map(sim, st)
    _apply_track(sim, st)
    _apply_waypoints(sim, st)
    _apply_poses(sim, st)
    _apply_params(sim, st)


def _apply_obstacles(sim, st: EditState) -> None:
    world = sim.world
    if st.obstacles_removed:
        world.obstacles[:] = [
            obs for obs in world.obstacles
            if obstacle_key(obs) not in st.obstacles_removed
        ]
    existing = {obstacle_key(obs) for obs in world.obstacles}
    for key, obs in st.obstacles_added.items():
        if key not in existing:
            world.add_obstacle((obs[0], obs[1]), radius=obs[2])
            existing.add(key)
    if st.obstacles_added or st.obstacles_removed:
        from . import commands

        commands._sync_obstacles(sim)


def _apply_recharge(sim, st: EditState) -> None:
    world = sim.world
    if st.recharge_removed:
        world.recharge_places[:] = [
            place for place in world.recharge_places
            if recharge_key(place) not in st.recharge_removed
        ]
    existing = {recharge_key(place) for place in world.recharge_places}
    for key, place in st.recharge_added.items():
        if key not in existing:
            world.recharge_places.append(np.array([place[0], place[1], 0.0]))
            existing.add(key)


def _apply_map(sim, st: EditState) -> None:
    if not st.map_set:
        return
    world = sim.world
    world_cfg = sim.config.setdefault("world", {})
    if st.map is None:
        world.grid_map = None
        sim.grid_map = None
        world.line_map = None
        world_cfg.pop("map_image", None)
        world_cfg.pop("line_map_image", None)
        return
    kind = st.map["kind"]
    path = st.map["path"]
    resolution = st.map["res"]
    if kind == "line":
        if st.track_set and st.track is not None:
            return  # the drawn track replaces the line map
        world.load_line_map(path, resolution)
        world_cfg["line_map_image"] = path
        world_cfg["resolution"] = resolution
    else:
        world.load_map(path, resolution)
        sim.grid_map = world.grid_map
        world_cfg["map_image"] = path
        world_cfg["resolution"] = resolution


def _apply_waypoints(sim, st: EditState) -> None:
    for robot, manager in enumerate(sim.waypoint_managers):
        removed = st.waypoints_removed.get(robot) or set()
        if removed:
            manager.waypoints[:] = [
                wp for wp in manager.waypoints
                if waypoint_key(wp) not in removed
            ]
            manager.current_index = min(manager.current_index, len(manager.waypoints))
        existing = {waypoint_key(wp) for wp in manager.waypoints}
        for key, wp in (st.waypoints_added.get(robot) or {}).items():
            if key not in existing:
                manager.add_waypoint(wp)
                existing.add(key)


def _apply_track(sim, st: EditState) -> None:
    if not st.track_set:
        return
    from . import commands

    if st.track is None:
        commands._track_clear(sim, {})
        return

    track = st.track
    commands._rasterize(
        sim,
        track.get("strokes") or [],
        fresh=True,
        default_width=float(track.get("line_width", 0.02)),
    )
    sim.apply_track()
    path = sim.config.setdefault("world", {}).get(
        "drawn_line_map_image", "config/line_drawn.png"
    )
    if sim._track_gray is not None:
        sim._track_gray.save(path)


def _apply_poses(sim, st: EditState) -> None:
    for robot, pose in st.poses.items():
        if not 0 <= robot < len(sim.robots):
            continue
        body = sim.robots[robot]
        if hasattr(body, "set_initial_pose"):
            body.set_initial_pose(pose[0], pose[1], pose[2])
        else:
            body.x, body.y, body.theta = pose
        if hasattr(body, "clear_path"):
            body.clear_path()


def _apply_params(sim, st: EditState) -> None:
    if not st.params:
        return
    from . import commands

    for name, value in st.params.items():
        commands._set_param(sim, {"name": name, "value": value})
