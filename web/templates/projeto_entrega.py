"""Atividade: projeto final de entrega autonoma.

O robo de entrega parte de (2, 2) e deve visitar as paradas de ENTREGAS na
ordem, desviando das caixas com o LiDAR. Complete forca_repulsiva() e a parte
angular de controle_entrega(). Ao terminar a rota, o script grava entrega.csv e
entrega.png e imprime ENTREGA CONCLUIDA.
"""

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from hivebr.engine import Simulator, load_config

ENTREGAS = [(5.0, 9.0), (10.0, 2.0), (15.0, 9.0), (18.0, 4.0)]
CAIXAS = [
    (7.5, 6.0, 0.8),
    (11.0, 5.0, 0.9),
    (13.5, 6.0, 0.7),
    (16.0, 2.5, 0.6),
]
ALCANCE_INFLUENCIA = 1.8
GANHO_REPULSAO = 1.7
VELOCIDADE_MAXIMA = 0.8
KP_ANG = 3.0
TOLERANCIA = 0.12


def normaliza(angulo):
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


def forca_atrativa(robot, goal):
    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return 0.0, 0.0
    return dx / dist, dy / dist


def forca_repulsiva(robot, lidar_readings):
    fx, fy = 0.0, 0.0
    for angulo, dist, _impacto in lidar_readings or []:
        if dist < ALCANCE_INFLUENCIA:
            forca = GANHO_REPULSAO * (ALCANCE_INFLUENCIA - dist) / ALCANCE_INFLUENCIA
            # TODO: acumule a repulsao oposta ao raio.
            pass
    return fx, fy


def controle_entrega(robot, world, goal, cfg, dt, lidar_readings=None):
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
    omega = max(-robot.max_omega, min(robot.max_omega, KP_ANG * erro))
    mais_perto = min([d for _, d, _ in lidar_readings or []] or [ALCANCE_INFLUENCIA])
    v = VELOCIDADE_MAXIMA * max(0.0, math.cos(erro)) * min(1.0, mais_perto / 0.8)
    return {"v": v, "omega": omega}


def salvar_entrega(trilha, caminho_csv="entrega.csv", caminho_png="entrega.png"):
    with Path(caminho_csv).open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["t", "x", "y"])
        for t, x, y in trilha:
            escritor.writerow([f"{t:.2f}", f"{x:.2f}", f"{y:.2f}"])

    plt.figure(figsize=(8, 5))
    plt.plot([p[1] for p in trilha], [p[2] for p in trilha], label="route")
    plt.scatter([p[0] for p in ENTREGAS], [p[1] for p in ENTREGAS], marker="*", label="stops")
    plt.xlabel("x (m)")
    plt.ylabel("y (m)")
    plt.title("Delivery route")
    plt.axis("equal")
    plt.grid(True)
    plt.legend()
    plt.savefig(caminho_png)
    plt.show()


def rodar(sim, limite=120.0):
    trilha = []
    while sim.running:
        sim.step()
        trilha.append((sim.sim_time, sim.robot.x, sim.robot.y))
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False
    return trilha, not sim.waypoints.has_waypoint()


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["lidar"] = {"enabled": True, "num_rays": 61, "range": 3.0, "fov_deg": 360}
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in CAIXAS]
    config["robot"]["initial_pose"] = [2.0, 2.0, 0.0]
    config["robot"]["radius"] = 0.2
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controle_entrega)
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in ENTREGAS])

    print(f"Entregas: {len(ENTREGAS)}")
    trilha, concluido = rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print(f"Colisoes: {len(sim.collision_events)}")
    if concluido:
        salvar_entrega(trilha)
        print("ENTREGA CONCLUIDA")
    print("Simulacao encerrada.")
