import sys
import os
from pathlib import Path
# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0,str(project_root))
sys.path.insert(0,str(project_root / "src"))
import time

import numpy as np
from hivebr.engine import Simulator, load_config, DataLogger

def normalize_angle(angle):
    """Normalize an angle to the range [-pi, pi]."""
    return np.arctan2(np.sin(angle), np.cos(angle))


def full_controller(robot,world,goal,cfg,dt,lidar_readings=None, r_tol = 0.2 ):

    if goal is None:
        return {
            "v": 0.0,
            "omega": 0.0
        }
    """
    Non-holonomic controller (position and orientation), considering transformation to polar coordinates Kanayama (1990).
    """
    
    # waypoint atual (alvo)    
    xd, yd, theta_d = goal[0], goal[1], goal[2]

    # Configuração atual do robô
    x, y, theta = robot.position[0], robot.position[1], robot.theta

    #### Verifica recarga
    p = np.array([x,y])
    id_recharge = 0    
    p_recharge = np.array(sim.world.recharge_places[id_recharge])
    dist_recharge_place = np.linalg.norm(p -p_recharge)
    # print(f"{robot.battery_percent} < {robot.critical_battery},{robot.going_to_recharge}, {robot.is_charging}")
    
    if dist_recharge_place <= r_tol and robot.battery_percent < robot.critical_battery and robot.going_to_recharge :
        print("Recharge")
        robot.set_charging()

    elif robot.is_charging:
        # robot.going_to_recharge = False
        # print("Recharging")
        # robot.update_battery(dt, charge_rate=20.0)
        # time.sleep(0.1)
        return {
            "v": 0.0,
            "omega": 0.0
        }
    elif robot.battery_percent <= robot.critical_battery and not robot.going_to_recharge:
        sim.go_to_recharge_place(id=id_recharge)
        print("Going to recharge.")

    # 1. Parâmetros de Controle
    kp = 3.5/10       # Ganho de posição
    k_alpha = 15/10  # Ganho de orientação para o alvo
    k_beta = -10 /10  # Ganho de orientação para o alinhamento final
    

    # 2. Transformação para coordenadas polares
    delta_x = xd - x
    delta_y = yd - y

    rho = np.linalg.norm([delta_x, delta_y]) # Distância ao alvo
    alpha = np.arctan2(delta_y, delta_x) - theta  # Ângulo para o alvo
    beta = theta_d - theta - alpha  # Ângulo para o alinhamento final

    alpha = normalize_angle(alpha)
    beta  = normalize_angle(beta)

    # Stop
    if (rho < r_tol):# and (np.abs(theta_d - theta) < np.deg2rad(5)):  # If close enough and aligned
        # print(f"Target reached! {rho:.4f} m away, {np.rad2deg(theta_d - theta):.2f}° angular difference.")
        # print(f"Current position: ({x:.4f}, {y:.4f}), Current orientation: {np.rad2deg(theta):.2f}°")
        return {
            "v": 0.0,
            "omega": 0.0
        }

    # 3. Ação de controle
    if np.abs(alpha) > np.pi/2 :
        # If target is behind, invert direction
        alpha = normalize_angle(alpha-np.pi)
        beta = normalize_angle(beta-np.pi)
        kp = -kp  # Invert gain to move backwards

    v = kp * rho  # Linear velocity proportional to distance 
    w = k_beta * beta + k_alpha * alpha  # Angular velocity combining alignment and orientation


    # 5. Saturação (Segurança Física)
    v_max = robot.max_speed  # m/s
    w_max = robot.max_omega  # rad/s
    v = max(min(v, v_max), -v_max)
    w = max(min(w, w_max), -w_max)

    
    return {
            "v": v,
            "omega": w
        }

def simple_controller(robot,world,goal,cfg,dt,lidar_readings=None):

    if goal is None:
        return {
            "v": 0.0,
            "omega": 0.0
        }
    """
    Non-holonomic controller based on position error (De Luca & Oriolo).
    """
    
    # waypoint atual (alvo)
    current_target = goal
    xd, yd = current_target[0], current_target[1]

    # Estado atual do robô
    x, y, theta = robot.position[0], robot.position[1], robot.theta

    # 1. Parâmetros de Controle (Sintonia)
    kp = 1.5       # Ganho de translação
    k_theta = 3.0  # Ganho de rotação
    r_tol = 0.1    # Raio de tolerância (chegou no alvo)

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

    # Returns (v, w) for the kinematic model of the simulator
    return {
            "v": v,
            "omega": w
        }


if __name__ == "__main__":

    # logger = DataLogger()

    sim = Simulator(controller=full_controller, type_robot="differential")     
    
    sim.set_using_orientation(True)  # Enable orientation control
    sim.set_goal_tolerance(0.2)  # Position tolerance to consider target reached (m)
    sim.robot.radius = 0.3
    # points = np.array([[13.78774011, 17.80954127],
    #    [11.40046318, 18.29715419],
    #    [10.74931352, 19.70334332],
    #    [ 8.66268298, 18.35323118],
    #    [ 5.80521278, 15.16896191],
    #    [ 6.37229174, 13.98530471],
    #    [ 6.29045338, 13.30539007],
    #    [ 4.88685739, 14.53175855],
    #    [ 3.97591282, 16.10761446],
    #    [ 4.2854486 , 17.32823795],
    #    [ 2.0114067 , 18.0083447 ],
    #    [ 0.86470512, 16.92614813],
    #    [ 0.84455451, 15.96763401],
    #    [ 0.47053438, 14.40592448],
    #    [ 4.23390592,  9.78923973],
    #    [ 5.24030901,  9.6520633 ],
    #    [ 6.16529342,  8.88084524],
    #    [ 8.13144625,  5.41311853],
    #    [ 6.99132212,  3.1958151 ],
    #    [ 6.07119843,  4.89408015],
    #    [ 4.24605402,  5.88546147],
    #    [ 0.36549214,  3.7107074 ],
    #    [ 0.24620752,  1.51130259],
    #    [ 8.71977192,  0.82459723],
    #    [11.47940976,  4.07407243],
    #    [13.38134013,  2.769291  ],
    #    [14.91013307,  6.51265064],
    #    [14.07989192,  5.72117444],
    #    [12.84897326,  7.60983658],
    #    [10.1844024 , 13.86136469],
    #    [11.31499598, 12.34257273],
    #    [13.29919254, 13.84672586],
    #    [13.7653074 , 13.14225301],
    #    [15.92293081, 10.55072134],
    #    [16.174035  ,  7.36000639],
    #    [16.14470896,  6.52164136],
    #    [19.85282756,  5.27662509],
    #    [19.95213895, 11.99954731],
    #    [16.96269257, 14.14697128],
    #    [16.88791677, 17.02181214],
    #    [13.78774011, 17.80954127]])
    
    points = np.array([[5,7],
       [8,1], [0,0], [6, 5], [9, 1]])
    points_o = []
    for p, p1 in zip(points, points[1:]):
        theta = np.arctan2(p1[1]-p[1], p1[0]-p[0])
        pi = np.array([p[0], p[1], theta])
        points_o.append(pi)
    points_o = np.array(points_o)
    # print(points_o)
    # points =  np.c_[points, np.nan*np.ones(len(points))]    
    # sim.waypoints.waypoints = list(points)
    sim.waypoints.waypoints = list(points_o)

    # sim.robot.x = points[0,0]
    # sim.robot.y = points[0,1]
    # sim.robot.theta = 0.0
    # sim.robot.set_initial_pose(points_o[0][0], points_o[0][1], points_o[0][2])
    
    sim.robot.set_battery_parameters(c_idle=0.1, c_v=4.0, c_w=1.0, critical_battery=50, working_battery=90)

    list_recharge_places = [[3, 3], [5,5], [9,9]]
    for rp in list_recharge_places:
        sim.world.recharge_places.append(rp)
    
    sim.run()

    # logger.save("logs/run_01.pkl")
    # logger.plot()