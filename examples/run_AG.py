import numpy as np
import heapq
import networkx as nx
from collections import deque
from hivebr.engine import Simulator, load_config
from hivebr.engine.map_generator import MapGenerator
from scipy.ndimage import binary_dilation
from scipy.ndimage import binary_dilation, zoom

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


class GeneticPlanner:
    def __init__(self, start, goal, grid_inflated, grid_shape, res):
        self.start = start
        self.goal = goal
        self.grid_inflated = grid_inflated
        self.height, self.width = grid_shape
        self.res = res
        self.num_waypoints = 10  # Número de waypoints no AG

    def fitness(self, chromosome):
        # Transforma o cromossomo (flat list) em waypoints
        path = [self.start]
        for i in range(0, len(chromosome), 2):
            path.append((chromosome[i], chromosome[i+1]))
        path.append(self.goal)

        # 1. Penalidade de colisão
        score = 0
        for (x, y) in path:
            col, row = world_to_grid(x, y, self.height, self.res)
            if not (0 <= col < self.width and 0 <= row < self.height) or self.grid_inflated[row, col]:
                return -10000  # Penalidade alta para colisão

        # 2. Penalidade de distância total (objetivo: minimizar)
        dist = 0
        for i in range(len(path)-1):
            dist += np.linalg.norm(np.array(path[i+1]) - np.array(path[i]))
        
        return 1.0 / (1.0 + dist) # Fitness é o inverso da distância

# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    res    = 0.1
    width  = 100
    height = 100
    seed = 43
    # 1. Gera grid
    grid_data = MapGenerator.create_grid(
    width=width,
    height=height,
    seed=seed,
    obstacle_rate=0.25,
    robot_radius=0.2,
    resolution=0.2,
    n_walls=1,
    wall_thickness=2,
    min_wall_length=5,
    type="circle",
    shape_type="circle"
)
    grid = np.array(grid_data[0], dtype=bool)

    # 2. Infla o grid para planejamento (mantém alta res para segurança)
    inflation_cells = int(np.ceil(0.2 / res))
    kernel          = np.ones((3, 3), dtype=bool)
    grid_inflated   = binary_dilation(grid, structure=kernel, iterations=inflation_cells)

    # 3. DOWN-SAMPLING: Cria grid de planejamento baseado em resolução
    # Para 10m x 10m com 256 células (16x16), res_low deve ser 0.625
    # (10m / 0.625 = 16)
    res_low = 0.5 
    world_width_m = 19.0
    world_height_m = 10.0
    
    target_width  = int(np.round(world_width_m / res_low))
    target_height = int(np.round(world_height_m / res_low))
    
    grid_low_res = zoom(grid_inflated.astype(float), 
                        (target_height / height, target_width / width), 
                        order=0).astype(bool)
    
    # Visualização do grid de baixa resolução
    print(f"\nGrid de Baixa Resolução ({target_width}x{target_height}):")
    for row in range(target_height):
        line = "".join(['#' if grid_low_res[row, col] else '.' for col in range(target_width)])
        print(line)
    print("-" * 20)

    # 4. Inicia simulador com o grid original (ALTA RES)
    sim = Simulator(controller=simple_controller, type_robot="differential")
    sim.set_using_orientation(False)
    sim.set_goal_tolerance(0.2)
    sim.set_map_from_grid(grid, resolution=res)
    sim.robot.radius = 0.2

    # 5. Define start e goal no frame mundo
    start_m = (1.0, 1.0)
    goal_m  = (8.0, 1.0)
    sim.robot.set_initial_pose(start_m[0], start_m[1], 0.0)

    # 6. Constrói grafo NetworkX sobre o GRID BAIXA RES
    G = nx.grid_2d_graph(target_width, target_height)
    G.remove_edges_from(list(G.edges()))

    for col in range(target_width):
        for row in range(target_height):
            for dc, dr in [(-1,0),(1,0),(0,-1),(0,1),
                           (-1,-1),(-1,1),(1,-1),(1,1)]:
                nc, nr = col + dc, row + dr
                if 0 <= nc < target_width and 0 <= nr < target_height:
                    G.add_edge((col, row), (nc, nr), weight=np.hypot(dc, dr))

    # Funções de conversão baseadas em resolução e alinhadas ao sistema do MapGenerator
    def world_to_low_res(x_m, y_m):
        col = int(np.clip(x_m / res_low, 0, target_width - 1))
        # O MapGenerator usa Y descrescente (row=0 é o topo)
        # O mundo usa Y crescente (y=0 é a base)
        row = int(np.clip((world_height_m - y_m) / res_low, 0, target_height - 1))
        return col, row

    def low_res_to_world(col, row):
        # Removido o + 0.5 para alinhar com o canto das células
        x = col * res_low
        y = world_height_m - (row * res_low)
        return round(float(x), 4), round(float(y), 4)

    # Validação de alinhamento
    start_px = world_to_low_res(*start_m)
    goal_px  = world_to_low_res(*goal_m)
    reconv_sx, reconv_sy = low_res_to_world(*start_px)
    reconv_gx, reconv_gy = low_res_to_world(*goal_px)
    print(f"DEBUG: Start {start_m} -> Grid {start_px} -> Reconv ({reconv_sx:.2f}, {reconv_sy:.2f})")
    print(f"DEBUG: Goal  {goal_m} -> Grid {goal_px} -> Reconv ({reconv_gx:.2f}, {reconv_gy:.2f})")

    # Remove nós ocupados, mas preserva START e GOAL
    nodes_to_remove = [
        (col, row)
        for col in range(target_width)
        for row in range(target_height)
        if grid_low_res[row, col] and (col, row) != start_px and (col, row) != goal_px
    ]
    G.remove_nodes_from(nodes_to_remove)

    if start_px in G and goal_px in G and nx.has_path(G, start_px, goal_px):
        h_dict = {n: np.hypot(n[0] - goal_px[0], n[1] - goal_px[1]) for n in G.nodes}
        a_estrela(G, start_px, goal_px, h_dict)
        
        path_grid = nx.shortest_path(G, start_px, goal_px, weight="weight")
        path_world = [low_res_to_world(*p) for p in path_grid]

        # Refinamento: Força início e fim exatos
        path_refined = list(path_world)
        path_refined[0]  = start_m
        path_refined[-1] = goal_m

        sim.waypoints.clear()
        for p in path_refined:
            pos = (p[0], p[1], 0.0)
            sim.waypoints.add_waypoint(list(pos))
        print(f"Caminho encontrado e adicionado ao simulador. Waypoints: {len(path_refined)}")
    else:
        print("Erro: Caminho não encontrado no grid de baixa resolução!")
        print(f"Start: {start_px}, Goal: {goal_px}")
        print(f"Start ocupado: {grid_low_res[start_px[1], start_px[0]]}")
        print(f"Goal ocupado: {grid_low_res[goal_px[1], goal_px[0]]}")

    print("Iniciando simulador...")
    sim.run()
    print("Simulador finalizado.")
