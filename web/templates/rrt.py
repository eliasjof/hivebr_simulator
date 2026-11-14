"""Atividade: planejamento de caminho com RRT.

O RRT cresce uma arvore de pontos aleatorios. A cada iteracao ele amostra um
ponto, encontra o no mais proximo, avanca um passo na direcao da amostra e
aceita o novo no se o segmento nao colidir com obstaculo.

As funcoes auxiliares (amostrar, mais_proximo, steer, sem_colisao) ja estao
prontas. Complete planejar_rrt() e devolva (caminho, arvore).

O console deve mostrar caminho=<numero de pontos> e uma figura deve aparecer.
"""

import math

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from hivebr.engine import Simulator, load_config

INICIO = np.array([2.0, 2.0])
ALVO = np.array([17.0, 9.0])
LIMITES = (0.5, 19.5, 0.5, 11.5)
OBSTACULOS = [(6.0, 4.0, 1.2), (11.0, 7.0, 1.4), (14.0, 3.5, 1.0)]
RAIO_ROBO = 0.2
MARGEM = 0.45
PASSO = 0.7
MAX_ITER = 4000
VIES = 0.15
SEED = 3
TOLERANCIA = 0.45

VMAX = 1.2
KP_DIST = 1.5
KP_ANG = 4.0


def distancia_segmento(p, q, c):
    v = q - p
    w = c - p
    denom = float(np.dot(v, v))
    if denom < 1e-12:
        return float(np.linalg.norm(w))
    t = max(0.0, min(1.0, float(np.dot(w, v)) / denom))
    return float(np.linalg.norm(w - t * v))


def sem_colisao(p, q):
    for ox, oy, raio in OBSTACULOS:
        if distancia_segmento(p, q, np.array([ox, oy])) <= raio + RAIO_ROBO + MARGEM:
            return False
    return True


def amostrar(rng):
    if rng.random() < VIES:
        return ALVO.copy()
    return np.array([rng.uniform(LIMITES[0], LIMITES[1]), rng.uniform(LIMITES[2], LIMITES[3])])


def mais_proximo(arvore, ponto):
    distancias = [np.linalg.norm(ponto - p) for p, _pai in arvore]
    return int(np.argmin(distancias))


def steer(origem, destino):
    delta = destino - origem
    norma = float(np.linalg.norm(delta))
    if norma < 1e-9:
        return origem.copy()
    return origem + delta / norma * min(PASSO, norma)


def caminho_ate(arvore, indice):
    caminho = []
    while indice is not None:
        caminho.append(arvore[indice][0])
        indice = arvore[indice][1]
    return caminho[::-1]


def planejar_rrt():
    """Devolve (caminho, arvore) ou (None, [])."""
    # TODO: crie a raiz com INICIO, itere MAX_ITER vezes, use amostrar,
    # mais_proximo, steer e sem_colisao; pare quando chegar perto de ALVO.
    return None, []


def normaliza(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controlador(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}
    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    dist = math.hypot(dx, dy)
    if dist < 0.08:
        return {"v": 0.0, "omega": 0.0}
    ang = normaliza(math.atan2(dy, dx) - robot.theta)
    v = min(VMAX, KP_DIST * dist) * max(0.0, math.cos(ang))
    omega = max(-robot.max_omega, min(robot.max_omega, KP_ANG * ang))
    return {"v": v, "omega": omega}


def rodar(sim, limite=90.0):
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    caminho, arvore = planejar_rrt()
    if caminho is None:
        print("RRT ainda nao implementado.")
        caminho = [INICIO]
    else:
        print(f"caminho={len(caminho)}")

    waypoints = [(float(p[0]), float(p[1]), math.nan) for p in caminho]

    config = load_config("config/default.yaml")
    config["robot"]["initial_pose"] = [INICIO[0], INICIO[1], 0.0]
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador)
    sim.set_robot_waypoints(0, waypoints)

    if arvore:
        fig, ax = plt.subplots(figsize=(7, 5))
        for ponto, pai in arvore:
            if pai is not None:
                origem = arvore[pai][0]
                ax.plot([origem[0], ponto[0]], [origem[1], ponto[1]], color="tab:blue", linewidth=0.5)
        ax.plot([p[0] for p in caminho], [p[1] for p in caminho], color="tab:red", linewidth=2)
        for ox, oy, raio in OBSTACULOS:
            ax.add_patch(Circle((ox, oy), raio, color="gray", alpha=0.5))
        ax.set_xlim(0, 20)
        ax.set_ylim(0, 12)
        ax.set_aspect("equal")
        ax.set_title("RRT")
        plt.show()

    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulacao encerrada.")
