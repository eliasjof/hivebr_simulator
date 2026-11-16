"""Activity: route planning in a warehouse with A*.

The 20 x 12 m arena is divided into 0.5 m cells. Occupied shelves are inflated
by the robot radius plus a margin. Complete heuristica(), planejar() and
reconstruir_caminho() to drive the robot from (2, 2) to (18, 9).

The console must print caminho=<number of cells>.
"""

import heapq
import math

import numpy as np

from hivebr.engine import Simulator, load_config

LARGURA, ALTURA = 20.0, 12.0
RESOLUCAO = 0.5
INICIO = (2.0, 2.0)
ALVO = (18.0, 9.0)
PRATELEIRAS = [(6.0, 4.0, 1.2), (11.0, 7.0, 1.4), (14.0, 3.5, 1.0)]
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
            for ox, oy, raio in PRATELEIRAS:
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
    """Estimated distance between two cells."""
    # TODO: use math.hypot(b[0] - a[0], b[1] - a[1]).
    return 0.0


def planejar(grade, inicio, objetivo):
    """Return (parents, expanded) or (None, 0)."""
    # TODO: use heapq, g and f costs and a closed set.
    return None, 0


def reconstruir_caminho(pais, inicio, objetivo):
    """Go back from the goal to the start using the parent dictionary."""
    # TODO: return the list of cells from start to goal.
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

    pais, expandidos = planejar(grade, inicio, objetivo)
    if pais is None:
        print("Planner not implemented yet.")
        caminho = [inicio]
    else:
        caminho = reconstruir_caminho(pais, inicio, objetivo)
        if not caminho:
            print("Path not found.")
            caminho = [inicio]
        else:
            print(f"caminho={len(caminho)}")

    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["robot"]["initial_pose"] = [INICIO[0], INICIO[1], 0.0]
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in PRATELEIRAS]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador)
    sim.set_robot_waypoints(0, caminho_para_waypoints(caminho))

    print(f"Free cells: {int((~grade).sum())}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulation finished.")
