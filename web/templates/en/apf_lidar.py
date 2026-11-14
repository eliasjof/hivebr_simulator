"""Activity: artificial potential field with LiDAR.

The robot must cross the corridor from (2, 6) to (17, 6). Every LiDAR ray close
to an obstacle pushes the robot away (repulsion); the goal pulls it forward
(attraction).

The attraction is already done. Complete the repulsion sum in forca_repulsiva.
Without it, the robot drives straight and collides.
"""

import math

import numpy as np

from hivebr.engine import Simulator, load_config

OBSTACULOS = [
    (7.0, 5.4, 0.8),
    (12.0, 6.8, 1.0),
    (15.0, 4.2, 0.6),
    (9.5, 3.3, 0.7),
]
ROTA = [(17.0, 6.0)]
ALCANCE_INFLUENCIA = 1.8   # m
GANHO_REPULSAO = 1.6
VELOCIDADE_MAXIMA = 0.8    # m/s
TOLERANCIA = 0.10          # m


def normaliza(angulo):
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


def forca_atrativa(robot, goal):
    """Unit vector pointing to the goal."""
    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return 0.0, 0.0
    return dx / dist, dy / dist


def forca_repulsiva(robot, lidar_readings):
    """Sum the repulsion of every ray inside ALCANCE_INFLUENCIA."""
    fx, fy = 0.0, 0.0
    for angulo, dist, _impacto in lidar_readings or []:
        if dist < ALCANCE_INFLUENCIA:
            forca = GANHO_REPULSAO * (ALCANCE_INFLUENCIA - dist) / ALCANCE_INFLUENCIA
            # TODO: accumulate the repulsion opposite to the ray.
            pass
    return fx, fy


def controlador_apf(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    if math.hypot(dx, dy) < TOLERANCIA:
        return {"v": 0.0, "omega": 0.0}

    ax, ay = forca_atrativa(robot, goal)
    rx, ry = forca_repulsiva(robot, lidar_readings)
    fx, fy = ax + rx, ay + ry

    if math.hypot(fx, fy) < 1e-6:
        return {"v": 0.0, "omega": 0.0}

    erro = normaliza(math.atan2(fy, fx) - robot.theta)
    omega = max(-robot.max_omega, min(robot.max_omega, 3.0 * erro))
    mais_perto = min([d for _, d, _ in lidar_readings or []] or [ALCANCE_INFLUENCIA])
    v = VELOCIDADE_MAXIMA * max(0.0, math.cos(erro)) * min(1.0, mais_perto / 0.8)
    return {"v": v, "omega": omega}


def rodar(sim, limite=60.0):
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["lidar"] = {"enabled": True, "num_rays": 61, "range": 3.0, "fov_deg": 360}
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["robot"]["initial_pose"] = [2.0, 6.0, 0.0]
    config["robot"]["radius"] = 0.2
    config["waypoints"]["goal_tolerance"] = 0.25

    sim = Simulator(config=config, controller=controlador_apf)
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in ROTA])

    print(f"Obstacles: {len(OBSTACULOS)}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print(f"Collisions: {len(sim.collision_events)}")
    print("Simulation finished.")
