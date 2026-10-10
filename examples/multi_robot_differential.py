"""Multi-robot differential-drive navigation.

Mirrors ``controle_robodiferencial.py`` (single B-bot, Kanayama controller) but
drives a fleet: every B-bot gets its own color, waypoint route and battery.
The same per-robot controller is called once per B-bot each step, and the
engine integrates all robots from a frozen snapshot (order independent).

Controls:
    Left click  -> add waypoint to the selected B-bot
    Right click -> add obstacle
    Keys 1..9   -> select B-bot
    Middle drag -> pan | mouse wheel -> zoom
"""

import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config


def normalize_angle(angle):
    return np.arctan2(np.sin(angle), np.cos(angle))


def full_controller(robot, world, goal, cfg, dt, lidar_readings=None, r_tol=0.2):
    """Non-holonomic position+orientation controller (Kanayama, 1990).

    Identical in spirit to the single-robot example, but receives the B-bot,
    its own goal and its own LiDAR readings because the engine dispatches one
    call per robot.
    """
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    xd, yd, theta_d = goal[0], goal[1], goal[2]
    x, y, theta = robot.position[0], robot.position[1], robot.theta

    if np.isnan(theta_d):
        theta_d = theta

    # 1. Control params
    kp = 3.5 / 10
    k_alpha = 15 / 10
    k_beta = -10 / 10

    # 2. Polar transform
    delta_x = xd - x
    delta_y = yd - y
    rho = np.linalg.norm([delta_x, delta_y])
    alpha = normalize_angle(np.arctan2(delta_y, delta_x) - theta)
    beta = normalize_angle(theta_d - theta - alpha)

    # Stop when the target is reached
    if rho < r_tol:
        return {"v": 0.0, "omega": 0.0}

    # 3. Control action
    if np.abs(alpha) > np.pi / 2:
        alpha = normalize_angle(alpha - np.pi)
        beta = normalize_angle(beta - np.pi)
        kp = -kp

    v = kp * rho
    w = k_beta * beta + k_alpha * alpha

    # 4. Safety saturation
    v = max(min(v, robot.max_speed), -robot.max_speed)
    w = max(min(w, robot.max_omega), -robot.max_omega)

    return {"v": v, "omega": w}


def route_with_orientation(points):
    """Turn a closed list of (x, y) into (x, y, theta) waypoints."""
    waypoints = []
    for p, p_next in zip(points, points[1:] + [points[0]]):
        theta = np.arctan2(p_next[1] - p[1], p_next[0] - p[0])
        waypoints.append(np.array([p[0], p[1], theta]))
    return waypoints


if __name__ == "__main__":
    config = load_config(project_root / "config" / "default.yaml")

    # ------------------------------------------------------------------
    # Fleet definition: each entry overrides the default robot config
    # ------------------------------------------------------------------
    config["robots"] = [
        {"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25},
        {"id": 1, "type": "differential", "initial_pose": [5.0, 5.0, 0.0], "radius": 0.25},
        {"id": 2, "type": "differential", "initial_pose": [18.0, 2.0, 0.0], "radius": 0.25},
        {"id": 3, "type": "differential", "initial_pose": [18.0, 10.0, 0.0], "radius": 0.25},
    ]

    # Robot-robot interaction policy
    config["interaction"] = {
        "collision_policy": "stop",
        "robot_safety_margin": 0.0,
        "resolve_push": 0.05,
        "comm_radius": None,
        "show_robot_links": True,
    }

    sim = Simulator(config=config, controller=full_controller)

    sim.set_using_orientation(True)
    sim.set_goal_tolerance(0.2)

    # ------------------------------------------------------------------
    # One patrol route per B-bot
    # ------------------------------------------------------------------
    routes = {
        0: [(2, 2), (5, 2), (5, 6), (2, 6)],
        1: [(5, 5), (10, 5), (10, 9), (5, 9)],
        2: [(18, 2), (15, 2), (15, 6), (18, 6)],
        3: [(18, 10), (14, 10), (14, 6), (18, 6)],
    }
    for index, points in routes.items():
        sim.set_robot_waypoints(index, route_with_orientation(points))

    # Battery model (optional per robot)
    for robot in sim.robots:
        robot.set_battery_parameters(c_idle=0.1, c_v=4.0, c_w=1.0, critical_battery=50, working_battery=90)

    serial = 0
    for rp in [[3, 3], [5, 5], [9, 9], [16, 3], [16, 9]]:
        sim.world.recharge_places.append(np.array([rp[0], rp[1], 0.0]))

    print(f"Fleet ready: {sim.num_robots} B-bots. Keys 1..{sim.num_robots} select a robot.")
    sim.run()
