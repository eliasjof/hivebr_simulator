"""Activity: reach the goal with a differential robot.

Implement the go-to-goal controller: compute the distance and the angle to the
goal, set v proportional to the distance and omega proportional to the angular
error.

The robot starts at (2, 2) and must reach (12, 9) without colliding.
"""

import math

from hivebr.engine import Simulator, load_config

ALVO = (12.0, 9.0)
VMAX = 1.2        # m/s
KP_DIST = 1.4
KP_ANG = 3.5
TOLERANCIA = 0.10  # m


def normaliza(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controle_go_to_goal(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    dist = math.hypot(dx, dy)
    if dist < TOLERANCIA:
        return {"v": 0.0, "omega": 0.0}

    ang = normaliza(math.atan2(dy, dx) - robot.theta)

    # TODO: v = min(VMAX, KP_DIST * dist) and omega = KP_ANG * ang.
    # Reduce v when the angular error is large.
    v = 0.0
    omega = 0.0

    return {"v": max(0.0, min(VMAX, v)), "omega": omega}


def rodar(sim, limite=60.0):
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["robot"]["initial_pose"] = [2.0, 2.0, 0.0]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controle_go_to_goal)
    sim.set_robot_waypoints(0, [(ALVO[0], ALVO[1], math.nan)])

    print(f"Goal: {ALVO}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulation finished.")
