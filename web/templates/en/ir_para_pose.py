"""Activity: reach the goal with a final orientation.

Besides reaching (12, 8), the robot must finish facing pi/2 (90 degrees).
The waypoint has three components: (x, y, theta).

Complete both stages: drive to the point and then rotate in place to the desired
angle. The controller receives goal=None once the waypoint is reached; at that
moment use ALVO to finish the alignment.
"""

import math

from hivebr.engine import Simulator, load_config

ALVO = (12.0, 8.0, math.pi / 2.0)
VMAX = 1.0
KP_DIST = 1.3
KP_ANG = 3.0
TOL_POS = 0.10   # m
TOL_ANG = 0.05   # rad


def normaliza(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controlador_pose(robot, world, goal, cfg, dt, lidar_readings=None):
    theta_goal = ALVO[2]
    if goal is None:
        alvo_x, alvo_y = ALVO[0], ALVO[1]
    else:
        alvo_x, alvo_y = float(goal[0]), float(goal[1])
        if len(goal) > 2 and not math.isnan(goal[2]):
            theta_goal = float(goal[2])

    dx = alvo_x - robot.x
    dy = alvo_y - robot.y
    dist = math.hypot(dx, dy)

    if dist > TOL_POS:
        ang = normaliza(math.atan2(dy, dx) - robot.theta)
        # TODO: drive toward the point (v and omega).
        v = 0.0
        omega = 0.0
    else:
        erro = normaliza(theta_goal - robot.theta)
        # TODO: rotate in place until the angular error is small.
        v = 0.0
        omega = 0.0

    return {"v": max(0.0, min(VMAX, v)), "omega": omega}


def concluiu(sim):
    if sim.waypoints.has_waypoint():
        return False
    erro = abs(normaliza(ALVO[2] - sim.robot.theta))
    return erro < TOL_ANG


def rodar(sim, limite=60.0):
    while sim.running:
        sim.step()
        if concluiu(sim) or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["robot"]["initial_pose"] = [2.0, 2.0, 0.0]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador_pose)
    sim.set_robot_waypoints(0, [ALVO])

    print(f"Goal with orientation: {ALVO}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print(f"Final angle: {math.degrees(sim.robot.theta):.1f} degrees")
    print("Simulation finished.")
