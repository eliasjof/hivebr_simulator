"""Multiple line-follower robots on the SAME track, starting from the SAME point.

Each B-bot uses a different set of PID gains, allowing comparison of
performance (lap time, total time, lap count) of distinct tuning strategies
under identical conditions.

Since all robots start from exactly the same point, robot-robot collision is
disabled via::

    config["interaction"] = {
        "collision_policy": "none",   # or robot_collision: False
        "robot_collision": False,
    }

Each robot's time appears in the info panel. Use the "Toggle Times" button
(or ``config["show_times"]``) to disable this visualization.

Default simulator controls:
    Space (Start button) -> start/pause simulation
    Middle mouse button  -> pan | mouse wheel -> zoom
    Toggle Times button  -> show/hide per-robot times

Track generation reference: ``examples/line_follower.py``.
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.geometry import clamp

from line_follower import (
    generate_random_track,
    pose_on_track,
)

TRACK_PATH = project_root / "config" / "line_track.png"

# ---------------------------------------------------------------------------
# PID Gain Sets Evaluated (one per robot)
# ---------------------------------------------------------------------------
GAIN_SETS = [
    {"base_speed": 0.30, "kp": 3.0, "ki": 0.00, "kd": 0.6, "integral_limit": 1.0},
    {"base_speed": 0.30, "kp": 10.0, "ki": 0.00, "kd": 0.0, "integral_limit": 1.0},
    {"base_speed": 0.30, "kp": 6.0, "ki": 0.00, "kd": 0.0, "integral_limit": 1.0},
    {"base_speed": 0.30, "kp": 28.0, "ki": 0.20, "kd": 1.6, "integral_limit": 1.0},
]

# Integral term state per robot (key = id(robot)).
_CTRL_STATE: dict[int, dict] = {}


def line_pid_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    """Line-following PID with PER-ROBOT gains.

    Gains come from ``robot.pid_params`` (set in ``main``). If missing,
    falls back to the global ``line_pid`` config block.
    """
    line_map = getattr(world, "line_map", None)
    if line_map is None or not hasattr(robot, "read_line_sensors"):
        return {"v": 0.0, "omega": 0.0}

    robot.read_line_sensors(line_map)
    error = robot.line_error

    pid = getattr(robot, "pid_params", None) or cfg.get("line_pid", {})
    base_speed = float(pid.get("base_speed", 0.35))
    kp = float(pid.get("kp", 3.0))
    ki = float(pid.get("ki", 0.0))
    kd = float(pid.get("kd", 0.8))
    integral_limit = float(pid.get("integral_limit", 1.0))

    state = _CTRL_STATE.setdefault(id(robot), {"integral": 0.0, "prev": 0.0})

    if robot.line_lost:
        state["integral"] = 0.0
        omega = 1.5 * (1.0 if error >= 0.0 else -1.0)
        velocity = base_speed * 0.4
    else:
        state["integral"] = clamp(
            state["integral"] + error * dt, -integral_limit, integral_limit
        )
        derivative = (error - state["prev"]) / dt if dt > 0.0 else 0.0
        omega = kp * error + ki * state["integral"] + kd * derivative
        velocity = base_speed * max(0.15, 1.0 - 0.6 * abs(error))

    state["prev"] = error

    velocity = clamp(velocity, 0.0, robot.max_speed)
    omega = clamp(omega, -robot.max_omega, robot.max_omega)
    return {"v": velocity, "omega": omega}


def resolve_gains(num_robots: int):
    """Repeats/truncates the gain list to the requested number of robots."""
    if num_robots <= len(GAIN_SETS):
        return GAIN_SETS[:num_robots]
    gains = []
    while len(gains) < num_robots:
        gains.append(GAIN_SETS[len(gains) % len(GAIN_SETS)])
    return gains


def main():
    parser = argparse.ArgumentParser(
        description="Multi line follower: same track, same start, different gains"
    )
    parser.add_argument("--seed", type=int, default=7, help="track random seed")
    parser.add_argument("--sensors", type=int, default=None, help="number of sensors (2, 5, or 8)")
    parser.add_argument("--robots", type=int, default=len(GAIN_SETS), help="number of robots")
    parser.add_argument(
        "--spread",
        type=float,
        default=0.0,
        help="lateral offset (m) between robots; 0 = all at same point",
    )
    parser.add_argument("--regenerate", action="store_true", help="force new track generation")
    args = parser.parse_args()

    num_robots = max(1, int(args.robots))
    gains = resolve_gains(num_robots)

    config = load_config(project_root / "config" / "line_follower.yaml")
    if args.sensors is not None:
        config["robot"]["num_sensors"] = int(args.sensors)

    if args.regenerate or not TRACK_PATH.exists():
        print(f"Generating random track (seed={args.seed}) -> {TRACK_PATH}")
    points = generate_random_track(TRACK_PATH, seed=args.seed)
    config["world"]["line_map_image"] = str(TRACK_PATH)

    # All robots start from the SAME point/tangent on the track.
    x0, y0, theta0 = pose_on_track(points)
    config["robots"] = [
        {
            "id": i,
            "type": "line_follower",
            "initial_pose": [x0, y0, theta0],
            "radius": float(config["robot"].get("radius", 0.05)),
        }
        for i in range(num_robots)
    ]

    # Do not evaluate robot-robot collision (they start overlapping).
    config["interaction"] = {
        "collision_policy": "none",
        "robot_collision": False,
        "robot_safety_margin": 0.0,
        "resolve_push": 0.0,
        "comm_radius": None,
        "show_robot_links": False,
    }

    # Per-robot time visualization (Toggle Times button in the panel).
    config["show_times"] = True

    sim = Simulator(config=config, controller=line_pid_controller)

    # Assign gains to each robot and optionally apply a small lateral
    # offset to help visualize individual trajectories.
    lateral = np.array([-math.sin(theta0), math.cos(theta0)])
    for i, robot in enumerate(sim.robots):
        robot.pid_params = dict(gains[i])
        if args.spread > 0.0:
            offset = (i - (num_robots - 1) / 2.0) * args.spread
            robot.set_initial_pose(x0 + lateral[0] * offset, y0 + lateral[1] * offset, theta0)

    # Camera is already auto-centered on the track by Simulator.__init__

    print(
        f"{num_robots} line follower robots | {sim.robots[0].num_sensors} sensors | "
        f"start point=({x0:.2f}, {y0:.2f}, {math.degrees(theta0):.1f}°) | "
        f"robot-robot collision: DISABLED"
    )
    for i, g in enumerate(gains):
        print(
            f"  B-Bot{i}: kp={g['kp']:.2f}, ki={g['ki']:.2f}, kd={g['kd']:.2f}, "
            f"v0={g['base_speed']:.2f}"
        )
    print("Click Start (or press Space) to begin.")

    sim.run()

    print("\n===== Per-Robot Results =====")
    for i, robot in enumerate(sim.robots):
        g = gains[i]
        stats = robot.lap_statistics()
        tag = f"B-Bot{i} (kp={g['kp']:.2f}, ki={g['ki']:.2f}, kd={g['kd']:.2f})"
        if stats["count"]:
            print(
                f"{tag}: {stats['count']} lap(s) | avg={stats['mean']:.2f}s | "
                f"best={stats['best']:.2f}s | worst={stats['worst']:.2f}s"
            )
        elif getattr(robot, "finished", False):
            print(f"{tag}: course completed in {robot.finish_time:.2f}s.")
        else:
            print(f"{tag}: ended at {robot.time:.2f}s without complete laps.")


if __name__ == "__main__":
    main()