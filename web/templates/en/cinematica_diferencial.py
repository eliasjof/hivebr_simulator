"""Activity: kinematics of a differential robot (v and omega).

A differential robot cannot move sideways: it drives with v and turns with
omega. Complete the controller to drive the robot from (2, 2) to (14, 6).

Hint: v points to the goal and omega corrects the heading error.
"""

import math

from hivebr.engine import Simulator, load_config

ALVO = (14.0, 6.0)
VELOCIDADE_MAXIMA = 1.0   # m/s
KP_DIST = 1.2
KP_ANG = 3.0
TOLERANCIA = 0.10         # m


def normaliza(angulo):
    """Return the equivalent angle in [-pi, pi]."""
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controlador_diferencial(robot, world, goal, cfg, dt, lidar_readings=None):
    """Return {"v", "omega"} for the differential robot."""
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    distancia = math.hypot(dx, dy)
    if distancia < TOLERANCIA:
        return {"v": 0.0, "omega": 0.0}

    erro = normaliza(math.atan2(dy, dx) - robot.theta)

    # TODO: use KP_DIST and KP_ANG to compute v and omega.
    v = 0.0
    omega = 0.0

    v = min(VELOCIDADE_MAXIMA, max(0.0, v))
    omega = max(-robot.max_omega, min(robot.max_omega, omega))
    return {"v": v, "omega": omega}


def rodar(sim, limite=60.0):
    """Run the simulation until the last waypoint or the time limit."""
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["robot"]["initial_pose"] = [2.0, 2.0, 0.0]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador_diferencial)
    sim.set_robot_waypoints(0, [(ALVO[0], ALVO[1], math.nan)])

    print(f"Goal: {ALVO}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulation finished.")
