"""Activity: path planning with A* on a grid.

A* is BFS with a priority queue: each cell has a cost g (steps from the start)
and a heuristic h (estimated distance to the goal). The queue sorts by f = g + h.

Complete heuristica(), astar() and reconstruir_caminho(). The console must show
expandidos=<number of expanded cells>.
"""

import heapq
import math
from collections import deque

import numpy as np

from hivebr.engine import Simulator, load_config

LARGURA, ALTURA = 20.0, 12.0
RESOLUCAO = 0.5
INICIO = (2.0, 2.0)
ALVO = (17.0, 9.0)
OBSTACULOS = [(6.0, 4.0, 1.2), (11.0, 7.0, 1.4), (14.0, 3.5, 1.0)]
RAIO_ROBO = 0.2
MARGEM = 0.45

VMAX = 1.2
KP_DIST = 1.5
KP_ANG = 4.0


def construir_grade():
    nx = int(LARGURA / RESOLUCAO)
    ny = int(ALTURA / RESOLUCAO)
    grade = np.zeros((nx, ny), dtype=bool)
    for i in range(nx):
        for j in range(ny):
            x = (i + 0.5) * RESOLUCAO
            y = (j + 0.5) * RESOLUCAO
            for ox, oy, raio in OBSTACULOS:
                if math.hypot(x - ox, y - oy) <= raio + RAIO_ROBO + MARGEM:
                    grade[i, j] = True
                    break
    return grade


def celula(ponto):
    return (int(ponto[0] / RESOLUCAO), int(ponto[1] / RESOLUCAO))


def centro(celula_):
    return ((celula_[0] + 0.5) * RESOLUCAO, (celula_[1] + 0.5) * RESOLUCAO)


def vizinhos(celula_, grade):
    x, y = celula_
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < grade.shape[0] and 0 <= ny < grade.shape[1] and not grade[nx, ny]:
            yield (nx, ny)


def heuristica(a, b):
    """Estimated distance between two cells (Manhattan or Euclidean)."""
    # TODO: use math.hypot or |dx| + |dy|.
    return 0.0


def astar(grade, inicio, objetivo):
    """Return (parents, expanded) or (None, 0)."""
    # TODO: use heapq, g and f costs and a closed set.
    return None, 0


def reconstruir_caminho(pais, inicio, objetivo):
    # TODO: walk back from the goal to the start using the parent dictionary.
    return None


def caminho_para_waypoints(caminho):
    return [(x, y, math.nan) for x, y in (centro(c) for c in caminho)]


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
    grade = construir_grade()
    inicio = celula(INICIO)
    objetivo = celula(ALVO)

    pais, expandidos = astar(grade, inicio, objetivo)
    if pais is None:
        print("A* not implemented yet.")
        caminho = [inicio]
    else:
        caminho = reconstruir_caminho(pais, inicio, objetivo)
        if not caminho:
            print("Path not found.")
            caminho = [inicio]
        else:
            print(f"expandidos={expandidos}")
            print(f"caminho={len(caminho)}")

    config = load_config("config/default.yaml")
    config["robot"]["initial_pose"] = [INICIO[0], INICIO[1], 0.0]
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador)
    sim.set_robot_waypoints(0, caminho_para_waypoints(caminho))

    print(f"Free cells: {int((~grade).sum())}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulation finished.")
