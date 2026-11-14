"""Atividade: chegar ao alvo com um robo diferencial.

Implemente o controlador "go-to-goal": calcule a distancia e o angulo ate o
alvo, defina v proporcional a distancia e omega proporcional ao erro angular.

O robo parte de (2, 2) e deve chegar a (12, 9) sem colidir.
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

    # TODO: v = min(VMAX, KP_DIST * dist) e omega = KP_ANG * ang.
    # Reduza v quando o erro angular for grande.
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

    print(f"Alvo: {ALVO}")
    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulacao encerrada.")
