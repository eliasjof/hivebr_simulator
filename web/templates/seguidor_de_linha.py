"""Seguidor de linha: um B-bot com sensores TCRT5000 e controlador PID.

Gera uma pista fechada aleatória (linha preta sobre fundo branco) em
config/line_track.png e põe o robô sobre ela. O PID usa só os sensores.
Como usar: a simulação inicia sozinha; os tempos das voltas saem no console.
"""

import math

import numpy as np
from PIL import Image, ImageDraw

from hivebr.engine import Simulator, load_config
from hivebr.engine.geometry import clamp


def gera_pista(semente=7):
    """Desenha a pista na imagem e devolve os pontos do centro da linha (m)."""
    res = 0.005  # metros por pixel; pista de 4 m x 3 m
    rng = np.random.default_rng(semente)
    t = np.linspace(0.0, 2.0 * np.pi, 2000, endpoint=False)
    raio = np.ones_like(t)
    for k in (2, 3, 4):  # ondulações suaves sobre uma elipse
        amplitude = rng.uniform(0.03, 0.08) / k
        fase = rng.uniform(0.0, 2.0 * np.pi)
        raio += amplitude * np.cos(k * t + fase)
    raio = np.clip(raio, 0.75, 1.05)
    xs = 2.0 + 1.44 * raio * np.cos(t)  # centro (2, 1.5) m; raios 1.44 m e 1.08 m
    ys = 1.5 + 1.08 * raio * np.sin(t)

    # Na imagem a linha 0 fica no topo (maior y do mundo): o eixo y é invertido.
    h_px = round(3.0 / res)
    pontos = [(x / res, (h_px - 1) - y / res) for x, y in zip(xs, ys)]
    imagem = Image.new("RGB", (round(4.0 / res), h_px), (255, 255, 255))
    ImageDraw.Draw(imagem).line(pontos + [pontos[0]], fill=(0, 0, 0), width=4, joint="curve")  # linha de 2 cm
    imagem.save("config/line_track.png")
    return np.column_stack([xs, ys])


def controlador_pid(robot, world, goal, cfg, dt, lidar_readings=None):
    """Lê os sensores de linha e devolve {"v", "omega"} com um PID."""
    robot.read_line_sensors(world.line_map)
    erro = robot.line_error  # -1: linha à direita; +1: à esquerda; 0: centrada
    pid = cfg["line_pid"]    # ganhos de config/line_follower.yaml

    if robot.line_lost:  # perdeu a linha: gira para o lado do último erro
        robot._integral = 0.0
        return {"v": 0.1, "omega": 1.5 if erro >= 0 else -1.5}

    # Integral (com limite) e derivada do erro.
    integral = clamp(getattr(robot, "_integral", 0.0) + erro * dt,
                     -pid["integral_limit"], pid["integral_limit"])
    derivada = (erro - getattr(robot, "_erro_anterior", erro)) / dt
    robot._integral, robot._erro_anterior = integral, erro

    omega = pid["kp"] * erro + pid["ki"] * integral + pid["kd"] * derivada
    v = pid["base_speed"] * max(0.15, 1.0 - 0.6 * abs(erro))  # mais devagar nas curvas
    return {"v": v, "omega": clamp(omega, -robot.max_omega, robot.max_omega)}


if __name__ == "__main__":
    config = load_config("config/line_follower.yaml")
    pontos = gera_pista(semente=7)
    config["world"]["line_map_image"] = "config/line_track.png"  # usa a pista recém-gerada

    # Pose inicial: sobre o primeiro ponto da linha, alinhada ao trecho seguinte.
    p0, p1 = pontos[0], pontos[12]
    sim = Simulator(config=config, controller=controlador_pid)
    sim.robot.set_initial_pose(float(p0[0]), float(p0[1]), math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    print(f"Sensores: {sim.robot.num_sensors}.")
    sim.run()

    stats = sim.robot.lap_statistics()
    if stats["count"]:
        print(f"Voltas: {stats['count']} | melhor: {stats['best']:.2f} s | média: {stats['mean']:.2f} s")
    else:
        print("Nenhuma volta completa.")
