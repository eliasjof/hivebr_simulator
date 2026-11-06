"""LiDAR and obstacle avoidance: a B-bot that goes around obstacles.

The LiDAR casts rays around the robot and returns, for each one, the angle, the
distance to the first obstacle and the hit point. The controller combines:
  - attraction: the goal pulls the robot forward;
  - repulsion: every ray that hits near an obstacle pushes the robot away.
The resulting direction sets the turn, and the speed drops when something is close.

How to use: the simulation starts by itself. The cyan lines are the LiDAR rays.
"""

import math

import numpy as np

from hivebr.engine import Simulator, load_config

# Circular obstacles (x, y, radius) in metres.
OBSTACULOS = [(7.0, 5.4, 0.8), (12.0, 6.8, 1.0), (15.0, 4.2, 0.6)]
ROTA = [(17.0, 6.0), (3.0, 6.0)]  # the robot goes back and forth between the two points
ALCANCE_INFLUENCIA = 1.5          # m; obstacles farther than this are ignored
GANHO_REPULSAO = 1.2
VELOCIDADE_MAXIMA = 0.8           # m/s


def normaliza_angulo(angulo):
    """Return the equivalent angle in the interval [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


def controlador_desvio(robot, world, goal, cfg, dt, lidar_readings=None):
    """Combine attraction to the goal and repulsion from the LiDAR rays."""
    if goal is None:
        return {"v": 0.0, "omega": 0.0}
    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    distancia = math.hypot(dx, dy)
    if distancia < 0.1:
        return {"v": 0.0, "omega": 0.0}

    # 1. Attraction: unit vector pointing at the goal.
    fx, fy = dx / distancia, dy / distancia

    # 2. Repulsion: lidar_readings is a list of (angle, distance, hit).
    mais_perto = ALCANCE_INFLUENCIA
    for angulo, dist, _impacto in lidar_readings or []:
        mais_perto = min(mais_perto, dist)
        if dist < ALCANCE_INFLUENCIA:
            forca = GANHO_REPULSAO * (ALCANCE_INFLUENCIA - dist) / ALCANCE_INFLUENCIA
            fx -= forca * math.cos(angulo)  # pushes opposite to the ray
            fy -= forca * math.sin(angulo)

    # 3. Turn towards the resulting direction; move only when facing it.
    erro = normaliza_angulo(math.atan2(fy, fx) - robot.theta)
    omega = max(-robot.max_omega, min(robot.max_omega, 3.0 * erro))
    v = VELOCIDADE_MAXIMA * max(0.0, math.cos(erro)) * min(1.0, mais_perto / 0.8)
    return {"v": v, "omega": omega}


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    # LiDAR on: 61 rays around the robot, 3 m range.
    config["lidar"] = {"enabled": True, "num_rays": 61, "range": 3.0, "fov_deg": 360}
    # The engine reads obstacles from config["obstacles"], with x, y and radius.
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["robot"]["initial_pose"] = [2.0, 6.0, 0.0]
    config["robot"]["radius"] = 0.2

    sim = Simulator(config=config, controller=controlador_desvio)
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in ROTA])

    print(f"{len(OBSTACULOS)} obstacles on the way.")
    sim.run()
    print("Simulation finished.")
