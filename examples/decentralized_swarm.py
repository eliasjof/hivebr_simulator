"""Decentralized swarm navigation using the hivebr OpenLab API.

Each B-bot is an independent ``HiveBrAgent`` instance and only sees its own
state plus its neighbors. The current waypoint arrives inside
``state.goal`` (``(x, y)`` or ``(x, y, theta)``), filled by the engine and
carried through the bridge.

The same script can later be pointed at the physical arena with
``backend="ros2"`` without touching the agent code.

Controls:
    Keys 1..N  -> select B-bot | Left click -> add waypoint | Right click -> obstacle
"""

import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config


def wrap(angle):
    return float((angle + np.pi) % (2.0 * np.pi) - np.pi)


class PatrolAgent(HiveBrAgent):
    """Decentralized Kanayama controller with local separation."""

    def setup(self):
        self.kp = self.params.get("kp", 0.35)
        self.k_alpha = self.params.get("k_alpha", 1.5)
        self.k_beta = self.params.get("k_beta", -1.0)
        # Goal tolerance straight from the engine config (YAML file), with an
        # explicit r_tol parameter and a default as fallbacks.
        self.r_tol = float(
            (self.cfg or {}).get("waypoints", {}).get(
                "goal_tolerance", self.params.get("r_tol", 0.2)
            )
        )
        self.sep_gain = self.params.get("sep_gain", 0.0)
        self.sep_margin = self.params.get("sep_margin", 0.35)

    def loop(self, state, neighbors):
        goal = state.goal
        if goal is None:
            return (0.0, 0.0)

        theta_d = goal[2] if len(goal) > 2 else state.theta
        dx = goal[0] - state.x
        dy = goal[1] - state.y
        rho = float(np.hypot(dx, dy))
        if rho < self.r_tol:
            return (0.0, 0.0)

        alpha = wrap(np.arctan2(dy, dx) - state.theta)
        beta = wrap(theta_d - state.theta - alpha)

        kp = self.kp
        if abs(alpha) > np.pi / 2:
            alpha = wrap(alpha - np.pi)
            beta = wrap(beta - np.pi)
            kp = -kp

        v = kp * rho
        w = self.k_beta * beta + self.k_alpha * alpha

        # Local reactive separation from surrounding B-bots
        for neighbor in neighbors.values():
            d = float(np.hypot(state.x - neighbor.x, state.y - neighbor.y))
            safe = state.radius + neighbor.radius + self.sep_margin
            if 0.0 < d < safe:
                v -= self.sep_gain * (safe - d)

        return (v, w)


def route_with_orientation(points):
    waypoints = []
    for p, p_next in zip(points, points[1:] + [points[0]]):
        theta = float(np.arctan2(p_next[1] - p[1], p_next[0] - p[0]))
        waypoints.append([p[0], p[1], theta])
    return waypoints


if __name__ == "__main__":
    config = load_config(project_root / "config" / "default.yaml")
    config["interaction"] = {
        "collision_policy": "stop",
        "robot_collision": True,
        "robot_safety_margin": 0.0,
        "resolve_push": 0.05,
        "comm_radius": 2.0,
        "show_robot_links": True,
    }
    # With robot_collision active, the LiDAR treats the other B-bots as
    # moving obstacles.
    config["lidar"]["enabled"] = True

    fleet = [
        {"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25},
        {"id": 1, "type": "differential", "initial_pose": [5.0, 5.0, 0.0], "radius": 0.25},
        {"id": 2, "type": "differential", "initial_pose": [18.0, 2.0, 0.0], "radius": 0.25},
        {"id": 3, "type": "differential", "initial_pose": [18.0, 10.0, 0.0], "radius": 0.25},
    ]

    exp = SwarmExperiment(
        robots=fleet,
        backend="navsim2d",
        config=config,
        orientation=True,
    )

    # Heterogeneous tuning: a bolder leader and more conservative followers
    exp.assign_agent(robot_id=0, agent_class=PatrolAgent, sep_gain=0.5, kp=0.45)
    exp.assign_agent(robot_ids=[1, 2, 3], agent_class=PatrolAgent, sep_gain=0.9)

    routes = {
        0: [(2, 2), (5, 2), (5, 6), (2, 6)],
        1: [(5, 5), (10, 5), (10, 9), (5, 9)],
        2: [(18, 2), (15, 2), (15, 6), (18, 6)],
        3: [(18, 10), (14, 10), (14, 6), (18, 6)],
    }
    for index, points in routes.items():
        exp.assign_route(index, route_with_orientation(points))

    print(f"Decentralized swarm ready: {len(fleet)} agents. Keys 1..{len(fleet)} select a B-bot.")
    exp.run()

    # In the decentralized mode the DataLogger lives inside the engine's
    # Simulator, created by the navsim2d backend. Use the experiment helpers to
    # save/plot it after the run (pickle by default, CSV via `save_log("x.csv")`).
    exp.save_log("decentralized_swarm_log.pkl")
    exp.print_collisions()
