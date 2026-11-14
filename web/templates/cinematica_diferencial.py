"""Atividade: cinematica de um robo diferencial (v e omega).

Um robo diferencial nao anda de lado: ele avanca com v e gira com omega.
Complete o controlador para levar o robo de (2, 2) ate (14, 6).

Dica: v aponta para o alvo e omega corrige o erro de direcao.
"""

import math

from hivebr.engine import Simulator, load_config

ALVO = (14.0, 6.0)
VELOCIDADE_MAXIMA = 1.0   # m/s
KP_DIST = 1.2
KP_ANG = 3.0
TOLERANCIA = 0.10         # m


def normaliza(angulo):
    """Devolve o angulo equivalente em [-pi, pi]."""
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controlador_diferencial(robot, world, goal, cfg, dt, lidar_readings=None):
    """Devolve {"v", "omega"} para o robo diferencial."""
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    distancia = math.hypot(dx, dy)
    if distancia < TOLERANCIA:
        return {"v": 0.0, "omega": 0.0}

    erro = normaliza(math.atan2(dy, dx) - robot.theta)

    # TODO: use KP_DIST e KP_ANG para calcular v e omega.
    v = 0.0
    omega = 0.0

    v = min(VELOCIDADE_MAXIMA, max(0.0, v))
    omega = max(-robot.max_omega, min(robot.max_omega, omega))
    return {"v": v, "omega": omega}


def rodar(sim, limite=60.0):
    """Roda a simulacao ate o ultimo waypoint ou ate o limite de tempo."""
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

    print(f"Alvo: {ALVO}")
    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulacao encerrada.")
