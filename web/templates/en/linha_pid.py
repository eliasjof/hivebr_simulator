"""Activity: line follower with a PID class.

The PID adds three actions: proportional (current error), integral (accumulated
error) and derivative (error variation). Complete the update() method of the
class and use the controller to complete one lap.

The normalized error ranges from -1 (line to the right) to +1 (line to the left).
"""

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from hivebr.engine import Simulator, load_config

TRACK_PATH = Path("config") / "line_track.png"
KP = 4.0
KI = 0.05
KD = 0.9
LIMITE_INTEGRAL = 1.0
BASE = 0.30


class ControladorPID:
    """Discrete PID with integral clamping."""

    def __init__(self, kp, ki, kd, limite_integral):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.limite_integral = float(limite_integral)
        self.integral = 0.0
        self.anterior = 0.0

    def update(self, erro, dt):
        """Return omega for the current error."""
        # TODO: accumulate integral, compute the derivative, apply the gains and
        # clamp the integral to [-limite_integral, +limite_integral].
        raise NotImplementedError


PID = ControladorPID(KP, KI, KD, LIMITE_INTEGRAL)


def gerar_pista(caminho=TRACK_PATH, largura=4.0, altura=3.0, resolucao=0.005, seed=7):
    rng = np.random.default_rng(seed)
    width_px = int(round(largura / resolucao))
    height_px = int(round(altura / resolucao))
    t = np.linspace(0.0, 2.0 * np.pi, 2000, endpoint=False)
    radius = np.ones_like(t)
    for k in (2, 3, 4):
        amplitude = rng.uniform(0.03, 0.08) / k
        phase = rng.uniform(0.0, 2.0 * np.pi)
        radius += amplitude * np.cos(k * t + phase)
    radius = np.clip(radius, 0.75, 1.05)

    cx, cy = largura / 2.0, altura / 2.0
    rx, ry = largura * 0.36, altura * 0.36
    xs = cx + rx * radius * np.cos(t)
    ys = cy + ry * radius * np.sin(t)

    image = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    line_px = max(1, int(round(0.02 / resolucao)))
    pontos = [(x / resolucao, (height_px - 1) - y / resolucao) for x, y in zip(xs, ys)]
    draw.line(pontos + [pontos[0]], fill=(0, 0, 0), width=line_px, joint="curve")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    image.save(caminho)
    return np.column_stack([xs, ys])


def pose_inicial(pontos, index=0, lookahead=12):
    n = len(pontos)
    p0 = pontos[index % n]
    p1 = pontos[(index + lookahead) % n]
    theta = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    return float(p0[0]), float(p0[1]), float(theta)


def controlador_pid(robot, world, goal, cfg, dt, lidar_readings=None):
    line_map = getattr(world, "line_map", None)
    if line_map is None or not hasattr(robot, "read_line_sensors"):
        return {"v": 0.0, "omega": 0.0}

    robot.read_line_sensors(line_map)
    erro = robot.line_error
    omega = PID.update(erro, dt)
    omega = max(-robot.max_omega, min(robot.max_omega, omega))
    return {"v": BASE, "omega": omega}


def rodar(sim, voltas=1, limite=90.0):
    while sim.running:
        sim.step()
        if len(sim.robot.lap_times) >= voltas or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/line_follower.yaml")
    pontos = gerar_pista()
    config["world"]["line_map_image"] = str(TRACK_PATH)

    sim = Simulator(config=config, controller=controlador_pid)
    x0, y0, theta0 = pose_inicial(pontos)
    sim.robot.set_initial_pose(x0, y0, theta0)

    print(f"Track: {len(pontos)} points")
    rodar(sim)

    print(f"Laps: {len(sim.robot.lap_times)}")
    if sim.robot.lap_times:
        print(f"Best lap: {min(sim.robot.lap_times):.2f} s")
    print("Simulation finished.")
