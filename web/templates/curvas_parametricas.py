"""Atividade: otimizacao de caminho com curvas parametricas.

Uma curva de Bezier e definida por pontos de controle. A curva resultante e
suave e pode ser otimizada para ficar curta e longe dos obstaculos.

Complete curva_bezier() (formula de Bernstein) e custo() (comprimento +
repulsao dos obstaculos + curvatura). A funcao otimizar() ja ajusta os pontos
de controle por descida de coordenadas.

A figura mostra os obstaculos, os pontos de controle e a curva final.
"""

import math

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

from hivebr.engine import Simulator, load_config

INICIO = (2.0, 2.0)
ALVO = (17.0, 9.0)
PONTOS = np.array([[2.0, 2.0], [5.0, 1.5], [9.0, 2.0], [13.0, 5.0], [17.0, 9.0]])
OBSTACULOS = [(6.0, 4.0, 1.2), (11.0, 7.0, 1.4), (14.0, 3.5, 1.0)]
RAIO_ROBO = 0.2
MARGEM = 0.45

VMAX = 1.2
KP_DIST = 1.5
KP_ANG = 4.0


def curva_bezier(pontos, t):
    """Avalia a curva de Bezier para os parametros t (array de 0 a 1)."""
    # TODO: use os polinomios de Bernstein. Devolva um array (len(t), 2).
    return None


def custo(pontos):
    """Custo do caminho: comprimento + repulsao dos obstaculos + curvatura."""
    # TODO: avalie a curva, some os segmentos e penalize a proximidade.
    return float("inf")


def otimizar(pontos, iteracoes=60, passo=0.3):
    melhor = pontos.copy()
    melhor_custo = custo(melhor)
    for _ in range(iteracoes):
        for i in range(1, len(melhor) - 1):
            for dx, dy in ((passo, 0.0), (-passo, 0.0), (0.0, passo), (0.0, -passo)):
                candidato = melhor.copy()
                candidato[i] += np.array([dx, dy])
                valor = custo(candidato)
                if valor < melhor_custo:
                    melhor, melhor_custo = candidato, valor
    return melhor


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
    ts = np.linspace(0.0, 1.0, 240)
    curva = curva_bezier(PONTOS, ts)
    if curva is None:
        print("Curva ainda nao implementada.")
        curva = np.array([INICIO, INICIO], dtype=float)
        pontos_otimizados = PONTOS
    else:
        pontos_otimizados = otimizar(PONTOS)
        curva = curva_bezier(pontos_otimizados, ts)
        if curva is None:
            curva = np.array([INICIO, ALVO], dtype=float)
        print(f"Pontos de controle: {len(pontos_otimizados)}")

    waypoints = [(float(p[0]), float(p[1]), math.nan) for p in curva[::12]]
    waypoints.append((float(curva[-1][0]), float(curva[-1][1]), math.nan))

    config = load_config("config/default.yaml")
    config["robot"]["initial_pose"] = [INICIO[0], INICIO[1], 0.0]
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador)
    sim.set_robot_waypoints(0, waypoints)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(curva[:, 0], curva[:, 1], color="tab:red", linewidth=2, label="curva")
    ax.plot(pontos_otimizados[:, 0], pontos_otimizados[:, 1], "o--", color="tab:blue", label="controle")
    for ox, oy, raio in OBSTACULOS:
        ax.add_patch(Circle((ox, oy), raio, color="gray", alpha=0.5))
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 12)
    ax.set_aspect("equal")
    ax.set_title("Parametric curves")
    ax.legend()
    plt.show()

    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulacao encerrada.")
