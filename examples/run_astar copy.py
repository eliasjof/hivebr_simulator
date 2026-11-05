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
import pygame
from hivebr.engine import Simulator, load_config
from hivebr.engine.map_generator import MapGenerator

########## Controlador
def simple_controller(robot,world,goal,cfg,dt,lidar_readings=None):

    if goal is None:
        return {
            "v": 0.0,
            "omega": 0.0
        }
    """
    Controlador não-holonômico baseado no erro de posição (De Luca & Oriolo).
    """
    
    # waypoint atual (alvo)
    current_target = goal
    xd, yd = current_target[0], current_target[1]

    # Estado atual do robô
    x, y, theta = robot.position[0], robot.position[1], robot.theta

    # 1. Parâmetros de Controle (Sintonia)
    kp = 1.5       # Ganho de translação
    k_theta = 3.0  # Ganho de rotação
    r_tol = float(cfg.get("waypoints", {}).get("goal_tolerance", 0.1))  # Tolerância (config)

    # 2. Dinâmica do Erro Posicional
    ex = xd - x
    ey = yd - y
    dist = np.linalg.norm([ex, ey])

    # Stop
    if dist < r_tol:
        return {
            "v": 0.0,
            "omega": 0.0
        }

    # 3. Encontro de Controle (u1 e u2)
    # De Luca & Oriolo propõem:     
    # u1 = kp * (ex * cos(theta) + ey * sin(theta))
    # u2 = k_theta * (atan2(ey, ex) - theta)
    v = kp * (ex * np.cos(theta) + ey * np.sin(theta))
    
    target_angle = np.arctan2(ey, ex)
    angle_error = target_angle - theta
    angle_error = np.arctan2(np.sin(angle_error), np.cos(angle_error))  # Normaliza para [-pi, pi]
    w = k_theta * angle_error

    # 5. Saturação (Segurança Física)
    v_max = robot.max_speed  # m/s
    w_max = robot.max_omega  # rad/s
    v = max(min(v, v_max), -v_max)
    w = max(min(w, w_max), -w_max)

    # Retorna (v, w) para a planta cinemática do simulador
    return {
            "v": v,
            "omega": w
        }
#######################################
# ALGORITMO A*
def a_star_grid(grid, start, goal, robot_radius=0.1375, resolution=0.2):
    # O grid original precisa ser inflado para considerar o tamanho do robô no A*
    from scipy.ndimage import binary_dilation
    
    # Inverter para alinhamento (0,0 bottom-left)
    grid_inverted = np.flipud(grid)
    
    # Inflar o grid com o raio do robô (em células)
    inflation_cells = int(np.ceil(robot_radius / resolution))
    structure = np.ones((3, 3), dtype=bool)
    grid_inflated = binary_dilation(grid_inverted, structure=structure, iterations=inflation_cells)
    
    height, width = grid_inflated.shape
    open_list = []
    heapq.heappush(open_list, (0, start))
    came_from = {}
    cost_so_far = {start: 0}
    
    while open_list:
        _, current = heapq.heappop(open_list)
        
        if current == goal:
            break
            
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]:
            neighbor = (current[0] + dx, current[1] + dy)
            
            if 0 <= neighbor[0] < width and 0 <= neighbor[1] < height:
                # Verifica colisão no grid INFLADO
                if not grid_inflated[neighbor[1], neighbor[0]]: 
                    new_cost = cost_so_far[current] + (np.sqrt(dx**2 + dy**2))
                    if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                        cost_so_far[neighbor] = new_cost
                        priority = new_cost + np.hypot(neighbor[0]-goal[0], neighbor[1]-goal[1])
                        heapq.heappush(open_list, (priority, neighbor))
                        came_from[neighbor] = current
                        
    # Reconstrução
    path = []
    curr = goal
    while curr in came_from:
        path.append(curr)
        curr = came_from[curr]
    path.append(start)
    return path[::-1]

######################################
sim = Simulator(controller=simple_controller,type_robot="differential")
sim.set_using_orientation(False)

# Gera mapa aleatório (create_grid retorna (grid, lista_de_obstáculos))
res = 0.1
grid, obstacles_list = MapGenerator.create_grid(width=100, height=100, type='random', obstacle_rate=0.25, robot_radius=0.0, seed=42, resolution=res)


# Inicia simulador
sim = Simulator(controller=simple_controller, type_robot="differential")
sim.set_using_orientation(False)
sim.set_goal_tolerance(0.2)
sim.set_map_from_grid(grid, resolution=res)

# Define o ponto inicial e final desejado
goal_m = (9.0, 9.0)
start_m = (1.0, 1.0)
sim.robot.set_initial_pose(start_m[0], start_m[1], 0.0)

###### Rodando o algoritmo A*
# Converter os pontos desejados de metros para grid (celulas)
start_px = (int(start_m[0] / res), int(start_m[1] / res))
goal_px = (int(goal_m[0] / res), int(goal_m[1] / res))

path_px = a_star_grid(grid, start_px, goal_px, robot_radius=sim.robot.radius, resolution=res)

# Converter pixels para mundo e adiciona no simulador
path_world = [sim.world.grid_map.grid_to_world(p[0], p[1]) for p in path_px]
sim.waypoints.clear()
for p in path_world:
    sim.waypoints.add_waypoint(list(p))

sim.run()
