"""Atividade: estacionar o robo na doca de carga.

O robo sai de (2, 6), vai ate a doca em (16, 6) e termina apontando para a
parede (theta = pi). Complete as duas etapas do controlador: aproximar e girar
no lugar. O console mostra a pose final.
"""

import math

from hivebr.engine import Simulator, load_config

DOCA = (16.0, 6.0)
THETA_DOCA = math.pi
VMAX = 0.9
KP_DIST = 1.2
KP_ANG = 3.0
KP_THETA = 2.5
TOL_POS = 0.12
TOL_ANG = 0.05


def normaliza(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controle_estacionamento(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        alvo_x, alvo_y = DOCA
    else:
        alvo_x, alvo_y = float(goal[0]), float(goal[1])

    dx = alvo_x - robot.x
    dy = alvo_y - robot.y
    distancia = math.hypot(dx, dy)

    if distancia > TOL_POS:
        # TODO: aproxime com v proporcional e omega = KP_ANG * erro.
        v = 0.0
        omega = 0.0
    else:
        # TODO: gire no lugar com omega = KP_THETA * (THETA_DOCA - theta).
        v = 0.0
        omega = 0.0

    omega = max(-robot.max_omega, min(robot.max_omega, omega))
    return {"v": max(0.0, min(VMAX, v)), "omega": omega}


def concluiu(sim):
    if sim.waypoints.has_waypoint():
        return False
    return abs(normaliza(THETA_DOCA - sim.robot.theta)) < TOL_ANG


def rodar(sim, limite=60.0):
    while sim.running:
        sim.step()
        if concluiu(sim) or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["obstacles"] = [
        {"x": 16.0, "y": 4.8, "radius": 0.35},
        {"x": 16.0, "y": 7.2, "radius": 0.35},
    ]
    config["robot"]["initial_pose"] = [2.0, 6.0, 0.0]
    config["waypoints"]["goal_tolerance"] = 0.20
    config["waypoints"]["define_orientation"] = True

    sim = Simulator(config=config, controller=controle_estacionamento)
    sim.set_robot_waypoints(0, [(DOCA[0], DOCA[1], THETA_DOCA)])

    print(f"Doca: {DOCA}")
    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print(f"Angulo final: {math.degrees(sim.robot.theta):.1f} graus")
    print("Simulacao encerrada.")
