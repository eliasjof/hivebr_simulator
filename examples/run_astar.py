import sys

import numpy as np
import os
from pathlib import Path
# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0,str(project_root))
sys.path.insert(0,str(project_root / "src"))
import heapq
import networkx as nx
from collections import deque
from hivebr.engine import Simulator, load_config
from hivebr.engine.map_generator import MapGenerator
from scipy.ndimage import binary_dilation


# ──────────────────────────────────────────────────────────────
# Controlador
# ──────────────────────────────────────────────────────────────

def simple_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    xd, yd    = goal[0], goal[1]
    x, y, theta = robot.position[0], robot.position[1], robot.theta

    kp      = 1.5
    k_theta = 3.0
    r_tol   = float(cfg.get("waypoints", {}).get("goal_tolerance", 0.1))

    ex   = xd - x
    ey   = yd - y
    dist = np.linalg.norm([ex, ey])

    if dist < r_tol:
        return {"v": 0.0, "omega": 0.0}

    v           = kp * (ex * np.cos(theta) + ey * np.sin(theta))
    angle_error = np.arctan2(np.sin(np.arctan2(ey, ex) - theta),
                             np.cos(np.arctan2(ey, ex) - theta))
    w = k_theta * angle_error

    v = np.clip(v, -robot.max_speed, robot.max_speed)
    w = np.clip(w, -robot.max_omega, robot.max_omega)
    return {"v": v, "omega": w}


# ──────────────────────────────────────────────────────────────
# Conversões mundo ↔ grid
#
# Convenção do MapGenerator: grid[row, col]
#   row=0  → topo da imagem  → Y mundo ALTO  (Y_world = H - row)
#   row=H-1→ base da imagem  → Y mundo BAIXO (Y_world ≈ 0)
#
# Nós do grafo NetworkX: (col, row) = (x_idx, y_idx)
#   col = índice de coluna  → eixo X mundo
#   row = índice de linha   → eixo Y mundo INVERTIDO
# ──────────────────────────────────────────────────────────────

def world_to_grid(x_m, y_m, grid_height, resolution):
    """
    Converte posição mundo (m) → (col, row) no grid top-left.

    x_m, y_m   : coordenadas no frame mundo (0,0 = bottom-left)
    grid_height : número de linhas do grid
    resolution  : metros por célula
    """
    col = int(np.floor(x_m / resolution))
    row = int(np.floor((grid_height * resolution - y_m) / resolution))
    # clamp para evitar fora dos limites por arredondamento
    row = max(0, min(row, grid_height - 1))
    return col, row


def grid_to_world(col, row, grid_height, resolution):
    """
    Converte (col, row) no grid top-left → centro da célula em mundo (m).

    row=0 está no topo da imagem → Y mundo alto.
    """
    x = (col + 0.5) * resolution
    y = (grid_height - row - 0.5) * resolution
    return x, y


# ──────────────────────────────────────────────────────────────
# Algoritmos de busca
# ──────────────────────────────────────────────────────────────

def mostrar_resultado(grafo, veio_de, inicio, objetivo, nome_algo):
    atual   = objetivo
    caminho = []
    while atual is not None and atual != inicio:
        caminho.append(atual)
        atual = veio_de.get(atual)
    if atual == inicio:
        caminho.append(inicio)
        caminho.reverse()
        print(f"\n{nome_algo}: {len(caminho)} nós encontrados.")
    else:
        print(f"\n{nome_algo}: Caminho não encontrado.")
    print("=" * 50)


def bfs(grafo, inicio, objetivo):
    fronteira = deque([inicio])
    veio_de   = {inicio: None}
    while fronteira:
        atual = fronteira.popleft()
        if atual == objetivo:
            break
        for vizinho in grafo.neighbors(atual):
            if vizinho not in veio_de:
                fronteira.append(vizinho)
                veio_de[vizinho] = atual
    mostrar_resultado(grafo, veio_de, inicio, objetivo, "BFS")
    return veio_de


def dijkstra(grafo, inicio, objetivo):
    fronteira       = [(0, inicio)]
    veio_de         = {inicio: None}
    custo_ate_agora = {inicio: 0}
    while fronteira:
        custo_atual, atual = heapq.heappop(fronteira)
        if atual == objetivo:
            break
        for vizinho in grafo.neighbors(atual):
            novo_custo = custo_ate_agora[atual] + grafo[atual][vizinho]["weight"]
            if vizinho not in custo_ate_agora or novo_custo < custo_ate_agora[vizinho]:
                custo_ate_agora[vizinho] = novo_custo
                heapq.heappush(fronteira, (novo_custo, vizinho))
                veio_de[vizinho] = atual
    mostrar_resultado(grafo, veio_de, inicio, objetivo, "DIJKSTRA")
    return veio_de


def a_estrela(grafo, inicio, objetivo, heuristica_dict):
    fronteira       = [(0, inicio)]
    veio_de         = {inicio: None}
    custo_ate_agora = {inicio: 0}
    while fronteira:
        _, atual = heapq.heappop(fronteira)
        if atual == objetivo:
            break
        for vizinho in grafo.neighbors(atual):
            novo_custo = custo_ate_agora[atual] + grafo[atual][vizinho]["weight"]
            if vizinho not in custo_ate_agora or novo_custo < custo_ate_agora[vizinho]:
                custo_ate_agora[vizinho] = novo_custo
                f = novo_custo + heuristica_dict.get(vizinho, 0)
                heapq.heappush(fronteira, (f, vizinho))
                veio_de[vizinho] = atual
    mostrar_resultado(grafo, veio_de, inicio, objetivo, "A*")
    return veio_de


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    res    = 0.1
    width  = 190
    height = 100

    # 1. Gera grid — convenção top-left: grid[row, col]
    #    row=0 → topo → Y mundo alto
    #    create_grid retorna (grid, lista_de_obstáculos)
    grid, obstacles_list = MapGenerator.create_grid(
        width, height,
        type="random",
        obstacle_rate=0.28,
        robot_radius=0.0,   # a inflação é feita explicitamente abaixo
        seed=42,
        resolution=res,
    )

    # 2. Infla o grid para planejamento
    #    IMPORTANTE: inflar o grid ORIGINAL (top-left)
    #    O grafo NetworkX vai usar este mesmo grid[row, col].
    inflation_cells = int(np.ceil(0.2 / res))   # raio do robô / resolução
    kernel          = np.ones((3, 3), dtype=bool)
    grid_inflated   = binary_dilation(
        grid, structure=kernel, iterations=inflation_cells
    )

    # 3. Inicia simulador com o grid original
    sim = Simulator(controller=simple_controller, type_robot="differential")
    sim.set_using_orientation(False)
    sim.set_goal_tolerance(0.2)
    sim.set_map_from_grid(grid, resolution=res)
    sim.robot.radius = 0.2

    # 4. Define start e goal no frame mundo
    start_m = (1.0, 1.0)
    goal_m  = (10.0, 1.0)
    sim.robot.set_initial_pose(start_m[0], start_m[1], 0.0)

    # 5. Converte para índices no grid top-left
    #    world_to_grid usa a inversão correta de Y
    start_px = world_to_grid(*start_m, height, res)
    goal_px  = world_to_grid(*goal_m,  height, res)

    print(f"Start mundo {start_m} -> grid {start_px} "
          f"-> reconvertido {grid_to_world(*start_px, height, res)}")
    print(f"Goal  mundo {goal_m}  -> grid {goal_px}  "
          f"-> reconvertido {grid_to_world(*goal_px,  height, res)}")

    # 6. Constrói grafo NetworkX sobre o grid INFLADO
    #    Nós: (col, row) — mesma indexação de grid_inflated[row, col]
    G = nx.grid_2d_graph(width, height)
    G.remove_edges_from(list(G.edges()))

    for col in range(width):
        for row in range(height):
            for dc, dr in [(-1,0),(1,0),(0,-1),(0,1),
                           (-1,-1),(-1,1),(1,-1),(1,1)]:
                nc, nr = col + dc, row + dr
                if 0 <= nc < width and 0 <= nr < height:
                    G.add_edge(
                        (col, row), (nc, nr),
                        weight=np.hypot(dc, dr)
                    )

    # Remove nós ocupados usando grid_inflated[row, col]
    G.remove_nodes_from([
        (col, row)
        for col in range(width)
        for row in range(height)
        if grid_inflated[row, col]
    ])

    # Verifica se start e goal estão no grafo
    if start_px in G and goal_px in G:        

        # 7. Heurística para A* — distância euclidiana ao goal em células
        h_dict = {
            n: np.hypot(n[0] - goal_px[0], n[1] - goal_px[1])
            for n in G.nodes
        }

        # 8. Roda A*
        a_estrela(G, start_px, goal_px, h_dict)

        # 9. Converte caminho de volta para mundo
        #    grid_to_world inverte Y corretamente
        path_grid = nx.shortest_path(
            G, start_px, goal_px, weight="weight"
        )

        path_world = [
            grid_to_world(col, row, height, res)
            for col, row in path_grid
        ]

        print(f"\nCaminho: {len(path_world)} waypoints")
        print(f"  Primeiro: {path_world[0]}  (esperado ~ {start_m})")
        print(f"  Último:   {path_world[-1]} (esperado ~ {goal_m})")

        # 10. Passa waypoints para o simulador
        sim.waypoints.clear()
        for p in path_world:
            sim.waypoints.add_waypoint(list(p))

    sim.run()