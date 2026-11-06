"""LiDAR e desvio de obstáculos: um B-bot que contorna obstáculos.

O LiDAR lança raios em volta do robô e devolve, para cada um, o ângulo, a
distância até o primeiro obstáculo e o ponto de impacto. O controlador combina:
  - atração: o objetivo puxa o robô para frente;
  - repulsão: cada raio que bate perto de um obstáculo empurra o robô para longe.
A direção resultante define o giro, e a velocidade cai quando há algo perto.

Como usar: a simulação inicia sozinha. As linhas ciano são os raios do LiDAR.
"""

import math

import numpy as np

from hivebr.engine import Simulator, load_config

# Obstáculos circulares (x, y, raio) em metros.
OBSTACULOS = [(7.0, 5.4, 0.8), (12.0, 6.8, 1.0), (15.0, 4.2, 0.6)]
ROTA = [(17.0, 6.0), (3.0, 6.0)]  # o robô vai e volta entre os dois pontos
ALCANCE_INFLUENCIA = 1.5          # m; obstáculos mais longe que isso são ignorados
GANHO_REPULSAO = 1.2
VELOCIDADE_MAXIMA = 0.8           # m/s


def normaliza_angulo(angulo):
    """Devolve o ângulo equivalente no intervalo [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


def controlador_desvio(robot, world, goal, cfg, dt, lidar_readings=None):
    """Combina atração ao alvo e repulsão dos raios do LiDAR."""
    if goal is None:
        return {"v": 0.0, "omega": 0.0}
    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    distancia = math.hypot(dx, dy)
    if distancia < 0.1:
        return {"v": 0.0, "omega": 0.0}

    # 1. Atração: vetor unitário apontando para o alvo.
    fx, fy = dx / distancia, dy / distancia

    # 2. Repulsão: lidar_readings é uma lista de (angulo, distancia, impacto).
    mais_perto = ALCANCE_INFLUENCIA
    for angulo, dist, _impacto in lidar_readings or []:
        mais_perto = min(mais_perto, dist)
        if dist < ALCANCE_INFLUENCIA:
            forca = GANHO_REPULSAO * (ALCANCE_INFLUENCIA - dist) / ALCANCE_INFLUENCIA
            fx -= forca * math.cos(angulo)  # empurra no sentido oposto ao raio
            fy -= forca * math.sin(angulo)

    # 3. Gira para a direção resultante; anda só quando está de frente.
    erro = normaliza_angulo(math.atan2(fy, fx) - robot.theta)
    omega = max(-robot.max_omega, min(robot.max_omega, 3.0 * erro))
    v = VELOCIDADE_MAXIMA * max(0.0, math.cos(erro)) * min(1.0, mais_perto / 0.8)
    return {"v": v, "omega": omega}


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    # LiDAR ligado: 61 raios em volta do robô, alcance de 3 m.
    config["lidar"] = {"enabled": True, "num_rays": 61, "range": 3.0, "fov_deg": 360}
    # O engine lê os obstáculos de config["obstacles"], com x, y e radius.
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["robot"]["initial_pose"] = [2.0, 6.0, 0.0]
    config["robot"]["radius"] = 0.2

    sim = Simulator(config=config, controller=controlador_desvio)
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in ROTA])

    print(f"{len(OBSTACULOS)} obstáculos no caminho.")
    sim.run()
    print("Simulação encerrada.")
