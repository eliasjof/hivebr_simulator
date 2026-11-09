"""Decentralized swarm with each B-bot controlled on its own CPU core.

The ``navsim2d`` backend normally calls every agent sequentially in the main
process. Because the engine computes the whole fleet's commands from a *frozen
snapshot* and only then integrates the kinematics, the per-agent control is
independent and can be parallelised.

Python's GIL blocks CPU parallelism with threads, so this example spreads the
controllers over a process pool (``concurrent.futures.ProcessPoolExecutor``),
one worker per CPU core. The pygame window stays in the main process; only the
controller math runs in the workers.

Controls:
    Keys 1..N  -> select B-bot | Left click -> add waypoint | Right click -> obstacle
"""

import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# The worker processes re-import this module (spawn start method on Windows and
# macOS), so their pygame import would print its banner once per worker. Keep
# the console readable.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config


def wrap(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def compute_control(sx, sy, stheta, goal, radius, max_speed, max_omega,
                    neighbors, r_tol=0.2, sep_gain=0.9, sep_steer=1.2,
                    sep_margin=0.35):
    """Pure-math Kanayama controller with local separation.

    This runs inside the worker processes, so it only receives plain numbers
    (no engine objects) and returns plain floats. ``r_tol`` must match the
    engine's ``waypoints.goal_tolerance`` (passed in by the caller), otherwise
    the B-bot stops short of the goal and the waypoint never advances.
    """
    if goal is None:
        return 0.0, 0.0

    gx, gy, gtheta = goal
    dx = gx - sx
    dy = gy - sy
    rho = math.hypot(dx, dy)
    if rho < r_tol:
        return 0.0, 0.0

    # Kanayama control in polar coordinates.
    kp, k_alpha, k_beta = 0.35, 1.5, -1.0
    alpha = wrap(math.atan2(dy, dx) - stheta)
    beta = wrap(gtheta - stheta - alpha)
    if abs(alpha) > math.pi / 2:
        alpha = wrap(alpha - math.pi)
        beta = wrap(beta - math.pi)
        kp = -kp

    v = kp * rho
    w = k_beta * beta + k_alpha * alpha

    # Reactive separation from the visible neighbors (also plain numbers).
    # The braking term only acts on neighbors that are *ahead* (in the forward
    # half-plane); braking on every neighbor makes two B-bots whose paths cross
    # cancel each other's forward speed and deadlock. A small steering term
    # biases the heading away from the neighbor so they go around instead.
    for nx, ny, nradius in neighbors:
        d = math.hypot(sx - nx, sy - ny)
        safe = radius + nradius + sep_margin
        if 0.0 < d < safe:
            shortfall = safe - d
            bearing = wrap(math.atan2(ny - sy, nx - sx) - stheta)
            v -= sep_gain * shortfall * max(0.0, math.cos(bearing))
            w -= sep_steer * shortfall * math.sin(bearing)

    v = max(-max_speed, min(max_speed, v))
    w = max(-max_omega, min(max_omega, w))
    return v, w


def _worker(task):
    """One task = one B-bot. Executed in a worker process."""
    (index, sx, sy, stheta, goal, radius, max_speed, max_omega, neighbors,
     r_tol) = task
    v, w = compute_control(sx, sy, stheta, goal, radius, max_speed, max_omega,
                           neighbors, r_tol)
    return index, v, w


def route_with_orientation(points):
    waypoints = []
    for p, p_next in zip(points, points[1:] + [points[0]]):
        theta = math.atan2(p_next[1] - p[1], p_next[0] - p[0])
        waypoints.append([p[0], p[1], theta])
    return waypoints


def make_parallel_fleet_controller(pool, comm_radius):
    """Build the engine ``fleet_controller`` that maps tasks over the pool."""

    def parallel_fleet_controller(robots, goals, config, dt, lidar_readings=None):
        """Engine seam: build one plain task per B-bot and map it over the pool."""
        # The stop radius has to match the engine's waypoint tolerance, so the
        # B-bot parks *inside* the tolerance circle and the waypoint advances.
        r_tol = float(config.get("waypoints", {}).get("goal_tolerance", 0.2))

        tasks = []
        for i, robot in enumerate(robots):
            goal = goals[i] if goals is not None else None
            if goal is not None:
                gtheta = float(goal[2]) if len(goal) > 2 else float(robot.theta)
                goal = (float(goal[0]), float(goal[1]), gtheta)

            # Visible neighbors: plain (x, y, radius) tuples, no engine objects.
            neighbors = []
            for j, other in enumerate(robots):
                if j == i:
                    continue
                if comm_radius is None or math.hypot(
                    robot.x - other.x, robot.y - other.y
                ) <= comm_radius:
                    neighbors.append((float(other.x), float(other.y), float(other.radius)))

            tasks.append((
                i, float(robot.x), float(robot.y), float(robot.theta), goal,
                float(robot.radius), float(robot.max_speed), float(robot.max_omega),
                neighbors, r_tol,
            ))

        commands = [{} for _ in robots]
        for index, v, w in pool.map(_worker, tasks):
            commands[index] = {"v": v, "omega": w}
        return commands

    return parallel_fleet_controller


def main():
    parser = argparse.ArgumentParser(
        description="Decentralized swarm with one worker process per CPU core"
    )
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1,
                        help="number of worker processes (default: all cores)")
    args = parser.parse_args()

    config = load_config(project_root / "config" / "default.yaml")
    config["interaction"] = {
        "collision_policy": "resolve",
        "robot_collision": True,
        "robot_safety_margin": 0.0,
        "resolve_push": 0.05,
        "comm_radius": 3.0,
        "show_robot_links": True,
    }
    config["lidar"]["enabled"] = True

    config["robots"] = [
        {"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25},
        {"id": 1, "type": "differential", "initial_pose": [5.0, 5.0, 0.0], "radius": 0.25},
        {"id": 2, "type": "differential", "initial_pose": [18.0, 2.0, 0.0], "radius": 0.25},
        {"id": 3, "type": "differential", "initial_pose": [18.0, 10.0, 0.0], "radius": 0.25},
    ]

    routes = {
        0: [(2, 2), (5, 2), (5, 6), (2, 6)],
        1: [(5, 5), (10, 5), (10, 9), (5, 9)],
        2: [(18, 2), (15, 2), (15, 6), (18, 6)],
        # B-bot 3 patrols the upper right. Its route must stay clear of B-bot 2:
        # two B-bots heading to the same (or nearly the same) point can never
        # both sit inside the goal tolerance without overlapping, so they would
        # deadlock against each other's separation term.
        3: [(18, 10), (14, 10), (14, 8), (18, 8)],
    }

    comm_radius = config["interaction"]["comm_radius"]
    pool = ProcessPoolExecutor(max_workers=max(1, args.workers))
    controller = make_parallel_fleet_controller(pool, comm_radius)

    sim = Simulator(config=config, fleet_controller=controller)
    for index, points in routes.items():
        sim.set_robot_waypoints(index, route_with_orientation(points))
    sim.set_using_orientation(True)

    print(
        f"Decentralized swarm: {sim.num_robots} B-bots, "
        f"controllers mapped over {max(1, args.workers)} worker process(es)."
    )
    sim.run()
    pool.shutdown()


if __name__ == "__main__":
    main()
