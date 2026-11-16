"""Atividade: campo potencial dentro de um tunel de inspecao.

O robo sai de (2, 6) e deve atravessar o tunel ate (18, 6). Os obstaculos
alternados e a coluna central sao obstaculos circulares. Complete a repulsao dos
raios do LiDAR e a componente tangencial que ajuda a escapar da coluna.

Sem a repulsao o robo anda em linha reta e colide. O console mostra o numero de
colisoes.
"""

import math

import numpy as np

from hivebr.engine import Simulator, load_config

OBSTACULOS = [
    (6.0, 4.5, 0.7), (10.0, 7.5, 0.7), (14.0, 4.5, 0.7),
    (12.0, 6.0, 0.7),
]
ROTA = [(18.0, 6.0)]
ALCANCE_INFLUENCIA = 1.8
GANHO_REPULSAO = 1.8
GANHO_TANGENCIAL = 0.8
VELOCIDADE_MAXIMA = 0.8
TOLERANCIA = 0.10


def normaliza(angulo):
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


def forca_atrativa(robot, goal):
    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return 0.0, 0.0
    return dx / dist, dy / dist


def forca_repulsiva(robot, lidar_readings):
    """Soma a repulsao dos raios dentro de ALCANCE_INFLUENCIA."""
    fx, fy = 0.0, 0.0
    for angulo, dist, _impacto in lidar_readings or []:
        if dist < ALCANCE_INFLUENCIA:
            forca = GANHO_REPULSAO * (ALCANCE_INFLUENCIA - dist) / ALCANCE_INFLUENCIA
            # TODO: acumule fx -= forca * cos(angulo) e fy -= forca * sin(angulo).
            pass
    return fx, fy


def componente_tangencial(fx, fy):
    """Gira a repulsao em 90 graus para o robo contornar a coluna."""
    # TODO: devolva (-fy, fx) quando a repulsao for forte; senao (0, 0).
    raise NotImplementedError


def controlador_apf(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    if math.hypot(dx, dy) < TOLERANCIA:
        return {"v": 0.0, "omega": 0.0}

    ax, ay = forca_atrativa(robot, goal)
    rx, ry = forca_repulsiva(robot, lidar_readings)
    tx, ty = componente_tangencial(rx, ry)
    fx, fy = ax + rx + tx, ay + ry + ty

    if math.hypot(fx, fy) < 1e-6:
        return {"v": 0.0, "omega": 0.0}

    erro = normaliza(math.atan2(fy, fx) - robot.theta)
    omega = max(-robot.max_omega, min(robot.max_omega, 3.0 * erro))
    mais_perto = min([d for _, d, _ in lidar_readings or []] or [ALCANCE_INFLUENCIA])
    v = VELOCIDADE_MAXIMA * max(0.0, math.cos(erro)) * min(1.0, mais_perto / 0.8)
    return {"v": v, "omega": omega}


def rodar(sim, limite=60.0):
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["lidar"] = {"enabled": True, "num_rays": 61, "range": 3.0, "fov_deg": 360}
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["robot"]["initial_pose"] = [2.0, 6.0, 0.0]
    config["robot"]["radius"] = 0.2
    config["waypoints"]["goal_tolerance"] = 0.25

    sim = Simulator(config=config, controller=controlador_apf)
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in ROTA])

    print(f"Obstaculos: {len(OBSTACULOS)}")
    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print(f"Colisoes: {len(sim.collision_events)}")
    print("Simulacao encerrada.")
