"""Atividade: cinematica de um robo holonomico (vx e vy).

O robo hexagonal aceita o comando {"vx", "vy"}: ele anda em qualquer direcao
sem precisar girar. Complete o controlador para levar o robo ate (12, 8).

Dica: vx e vy devem ser proporcionais a dx e dy; limite a norma do vetor.
"""

import math

from hivebr.engine import Simulator, load_config

ALVO = (12.0, 8.0)
GANHO = 1.2               # m/s por metro de distancia
VELOCIDADE_MAXIMA = 1.5   # m/s
TOLERANCIA = 0.10         # m


def controlador_holonomico(robot, world, goal, cfg, dt, lidar_readings=None):
    """Devolve {"vx", "vy"} para o robo holonomico."""
    if goal is None:
        return {"vx": 0.0, "vy": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    if math.hypot(dx, dy) < TOLERANCIA:
        return {"vx": 0.0, "vy": 0.0}

    # TODO: calcule vx = GANHO * dx e vy = GANHO * dy.
    vx = 0.0
    vy = 0.0

    total = math.hypot(vx, vy)
    if total > VELOCIDADE_MAXIMA:
        vx *= VELOCIDADE_MAXIMA / total
        vy *= VELOCIDADE_MAXIMA / total
    return {"vx": vx, "vy": vy}


def rodar(sim, limite=60.0):
    """Roda a simulacao ate o ultimo waypoint ou ate o limite de tempo."""
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["robot"].update({
        "type": "hexagonal_holonomic",
        "initial_pose": [2.0, 2.0, 0.0],
        "radius": 0.3,
        "wheel_radius": 0.05,
        "max_wheel_speed": 20.0,
    })
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador_holonomico)
    sim.set_robot_waypoints(0, [(ALVO[0], ALVO[1], math.nan)])

    print(f"Alvo: {ALVO}")
    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulacao encerrada.")
