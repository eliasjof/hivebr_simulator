"""Dijkstra path planning on a random grid, driven in the hivebr engine.

Same scene conventions as ``run_astar.py`` (grid stored top-left, Y inverted),
but the shortest path is searched with **Dijkstra** instead of A*.

Run with:
    python examples/run_dijkstra.py
"""

import sys
from pathlib import Path

import numpy as np
import heapq
import networkx as nx
from collections import deque

# ──────────────────────────────────────────────────────────────
# Path / imports
# ──────────────────────────────────────────────────────────────

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator  # noqa: E402
from hivebr.engine.map_generator import MapGenerator  # noqa: E402
from scipy.ndimage import binary_dilation  # noqa: E402


# ──────────────────────────────────────────────────────────────
# Controller
# ──────────────────────────────────────────────────────────────

def simple_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    xd, yd = goal[0], goal[1]
    x, y, theta = robot.position[0], robot.position[1], robot.theta

    kp = 1.5
    k_theta = 3.0
    r_tol = float(cfg.get("waypoints", {}).get("goal_tolerance", 0.1))

    ex = xd - x
    ey = yd - y
    dist = np.linalg.norm([ex, ey])

    if dist < r_tol:
        return {"v": 0.0, "omega": 0.0}

    v = kp * (ex * np.cos(theta) + ey * np.sin(theta))
    angle_error = np.arctan2(np.sin(np.arctan2(ey, ex) - theta),
                             np.cos(np.arctan2(ey, ex) - theta))
    w = k_theta * angle_error

    v = np.clip(v, -robot.max_speed, robot.max_speed)
    w = np.clip(w, -robot.max_omega, robot.max_omega)
    return {"v": v, "omega": w}


# ──────────────────────────────────────────────────────────────
# World <-> grid conversions (convention: grid[row, col], top-left)
# ──────────────────────────────────────────────────────────────

def world_to_grid(x_m, y_m, grid_height, resolution):
    col = int(np.floor(x_m / resolution))
    row = int(np.floor((grid_height * resolution - y_m) / resolution))
    row = max(0, min(row, grid_height - 1))
    return col, row


def grid_to_world(col, row, grid_height, resolution):
    x = (col + 0.5) * resolution
    y = (grid_height - row - 0.5) * resolution
    return x, y


# ──────────────────────────────────────────────────────────────
# Search algorithms
# ──────────────────────────────────────────────────────────────

def mostrar_resultado(veio_de, inicio, objetivo, nome_algo):
    atual = objetivo
    caminho = []
    while atual is not None and atual != inicio:
        caminho.append(atual)
        atual = veio_de.get(atual)
    if atual == inicio:
        caminho.append(inicio)
        caminho.reverse()
        print(f"\n{nome_algo}: {len(caminho)} nos encontrados.")
    else:
        print(f"\n{nome_algo}: Caminho nao encontrado.")
    print("=" * 50)


def bfs(grafo, inicio, objetivo):
    fronteira = deque([inicio])
    veio_de = {inicio: None}
    while fronteira:
        atual = fronteira.popleft()
        if atual == objetivo:
            break
        for vizinho in grafo.neighbors(atual):
            if vizinho not in veio_de:
                fronteira.append(vizinho)
                veio_de[vizinho] = atual
    mostrar_resultado(veio_de, inicio, objetivo, "BFS")
    return veio_de


def dijkstra(grafo, inicio, objetivo):
    fronteira = [(0.0, inicio)]
    veio_de = {inicio: None}
    custo_ate_agora = {inicio: 0.0}
    visitados = set()

    while fronteira:
        custo_atual, atual = heapq.heappop(fronteira)
        if atual in visitados:
            continue
        visitados.add(atual)
        if atual == objetivo:
            break
        for vizinho in grafo.neighbors(atual):
            novo_custo = custo_atual + grafo[atual][vizinho]["weight"]
            if vizinho not in custo_ate_agora or novo_custo < custo_ate_agora[vizinho]:
                custo_ate_agora[vizinho] = novo_custo
                heapq.heappush(fronteira, (novo_custo, vizinho))
                veio_de[vizinho] = atual

    mostrar_resultado(veio_de, inicio, objetivo, "DIJKSTRA")
    return veio_de


def reconstruct_path(veio_de, inicio, objetivo):
    if objetivo not in veio_de:
        return None
    path = []
    atual = objetivo
    while atual is not None:
        path.append(atual)
        atual = veio_de[atual]
    path.reverse()
    if path[0] != inicio:
        return None
    return path


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    res = 0.1
    width = 190
    height = 100

    # 1. Random grid (create_grid returns (grid, obstacles))
    grid, obstacles_list = MapGenerator.create_grid(
        width, height,
        type="random",
        obstacle_rate=0.28,
        robot_radius=0.0,   # inflation done explicitly below
        seed=42,
        resolution=res,
    )

    # 2. Inflate the raw grid for planning
    inflation_cells = int(np.ceil(0.2 / res))
    kernel = np.ones((3, 3), dtype=bool)
    grid_inflated = binary_dilation(grid, structure=kernel, iterations=inflation_cells)

    # 3. Simulator / robot
    sim = Simulator(controller=simple_controller, type_robot="differential")
    sim.set_using_orientation(False)
    sim.set_goal_tolerance(0.2)
    sim.set_map_from_grid(grid, resolution=res)
    sim.robot.radius = 0.2

    # 4. Start / goal in world coordinates
    start_m = (1.0, 1.0)
    goal_m = (10.0, 1.0)
    sim.robot.set_initial_pose(start_m[0], start_m[1], 0.0)

    start_px = world_to_grid(*start_m, height, res)
    goal_px = world_to_grid(*goal_m, height, res)

    print(f"Start mundo {start_m} -> grid {start_px} "
          f"-> reconvertido {grid_to_world(*start_px, height, res)}")
    print(f"Goal  mundo {goal_m}  -> grid {goal_px}  "
          f"-> reconvertido {grid_to_world(*goal_px, height, res)}")

    # 5. Build the NetworkX graph over the inflated grid
    G = nx.grid_2d_graph(width, height)
    G.remove_edges_from(list(G.edges()))

    for col in range(width):
        for row in range(height):
            for dc, dr in [(-1, 0), (1, 0), (0, -1), (0, 1),
                           (-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nc, nr = col + dc, row + dr
                if 0 <= nc < width and 0 <= nr < height:
                    G.add_edge((col, row), (nc, nr),
                               weight=float(np.hypot(dc, dr)))

    G.remove_nodes_from([
        (col, row)
        for col in range(width)
        for row in range(height)
        if grid_inflated[row, col]
    ])

    if start_px in G and goal_px in G:

        # 6. Dijkstra search
        veio_de = dijkstra(G, start_px, goal_px)

        path_grid = reconstruct_path(veio_de, start_px, goal_px)

        if path_grid is None:
            print("Dijkstra nao encontrou caminho; usando NetworkX fallback.")
            path_grid = nx.shortest_path(G, start_px, goal_px, weight="weight")

        path_world = [
            grid_to_world(col, row, height, res)
            for col, row in path_grid
        ]

        print(f"\nCaminho: {len(path_world)} waypoints")
        print(f"  Primeiro: {path_world[0]}  (esperado ~ {start_m})")
        print(f"  Ultimo:   {path_world[-1]} (esperado ~ {goal_m})")

        # 7. Feed the waypoints to the simulator
        sim.waypoints.clear()
        for p in path_world:
            sim.waypoints.add_waypoint(list(p))

    sim.run()
