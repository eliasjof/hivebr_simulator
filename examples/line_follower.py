"""Seguidor de linha com robô diferencial e sensores analógicos TCRT5000.

O script:
  1. Gera uma trajetória aleatória fechada e a salva como imagem (linha preta
     de 2 cm sobre fundo branco) em ``config/line_track.png``.
  2. Carrega ``config/line_follower.yaml``.
  3. Posiciona o robô sobre a linha, alinhado à tangente da pista.
  4. Executa um controlador PID que usa apenas as leituras dos sensores
     analógicos (2, 5 ou 8 TCRT5000) para seguir a linha.

Controles padrão do simulador:
    Espaço (botão Start) -> inicia/pausa a simulação
    Botão do meio      -> arrastar (pan) | roda do mouse -> zoom
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.geometry import clamp

TRACK_PATH = project_root / "config" / "line_track.png"


# ---------------------------------------------------------------------------
# Geração da trajetória aleatória
# ---------------------------------------------------------------------------
def generate_random_track(
    path: Path,
    width_m: float = 4.0,
    height_m: float = 3.0,
    resolution: float = 0.005,
    line_width_m: float = 0.02,
    seed: int = 7,
):
    """Cria uma pista fechada aleatória e a desenha como linha preta.

    A curva é uma perturbação suave (série de Fourier) de uma elipse, o que
    garante uma trajetória fechada e com curvatura suave, adequada para um
    seguidor de linha. Retorna os pontos do centro da linha em coordenadas de
    mundo (metros).
    """
    rng = np.random.default_rng(seed)
    width_px = int(round(width_m / resolution))
    height_px = int(round(height_m / resolution))

    t = np.linspace(0.0, 2.0 * np.pi, 2000, endpoint=False)
    radius = np.ones_like(t)
    for k in (2, 3, 4):
        amplitude = rng.uniform(0.03, 0.08) / k
        phase = rng.uniform(0.0, 2.0 * np.pi)
        radius += amplitude * np.cos(k * t + phase)
    radius = np.clip(radius, 0.75, 1.05)

    cx, cy = width_m / 2.0, height_m / 2.0
    rx, ry = width_m * 0.36, height_m * 0.36
    xs = cx + rx * radius * np.cos(t)
    ys = cy + ry * radius * np.sin(t)

    image = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    line_px = max(1, int(round(line_width_m / resolution)))
    points_px = [
        (x / resolution, (height_px - 1) - y / resolution)
        for x, y in zip(xs, ys)
    ]
    draw.line(points_px + [points_px[0]], fill=(0, 0, 0), width=line_px, joint="curve")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)

    return np.column_stack([xs, ys])


# ---------------------------------------------------------------------------
# Controlador PID de seguimento de linha
# ---------------------------------------------------------------------------
_CTRL_STATE: dict[int, dict] = {}


def line_pid_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    """Controlador PID que segue a linha usando apenas os sensores de linha.

    O erro normalizado (``robot.line_error``) vale ``-1`` quando a linha está
    totalmente à direita do robô, ``+1`` quando está totalmente à esquerda e
    ``0`` quando centrada. Como o robô é diferencial, ``omega`` corrige o
    desvio e ``v`` é reduzido nas curvas.
    """
    line_map = getattr(world, "line_map", None)
    if line_map is None or not hasattr(robot, "read_line_sensors"):
        return {"v": 0.0, "omega": 0.0}

    robot.read_line_sensors(line_map)
    error = robot.line_error

    pid = cfg.get("line_pid", {})
    base_speed = float(pid.get("base_speed", 0.35))
    kp = float(pid.get("kp", 3.0))
    ki = float(pid.get("ki", 0.0))
    kd = float(pid.get("kd", 0.8))
    integral_limit = float(pid.get("integral_limit", 1.0))

    state = _CTRL_STATE.setdefault(id(robot), {"integral": 0.0, "prev": 0.0})

    if robot.line_lost:
        # Linha perdida: gira devagar na direção do último erro conhecido.
        state["integral"] = 0.0
        omega = 1.5 * (1.0 if error >= 0.0 else -1.0)
        velocity = base_speed * 0.4
    else:
        state["integral"] = clamp(
            state["integral"] + error * dt, -integral_limit, integral_limit
        )
        derivative = (error - state["prev"]) / dt if dt > 0.0 else 0.0
        omega = kp * error + ki * state["integral"] + kd * derivative
        # Reduz a velocidade em desvios grandes para dar tempo de corrigir.
        velocity = base_speed * max(0.15, 1.0 - 0.6 * abs(error))

    state["prev"] = error

    velocity = clamp(velocity, 0.0, robot.max_speed)
    omega = clamp(omega, -robot.max_omega, robot.max_omega)
    return {"v": velocity, "omega": omega}


# ---------------------------------------------------------------------------
# Configuração de pose inicial a partir da pista
# ---------------------------------------------------------------------------
def pose_on_track(points: np.ndarray, index: int = 0, lookahead: int = 12):
    """Retorna ``(x, y, theta)`` sobre a pista, alinhado à tangente."""
    n = len(points)
    p0 = points[index % n]
    p1 = points[(index + lookahead) % n]
    theta = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    return float(p0[0]), float(p0[1]), float(theta)


def main():
    parser = argparse.ArgumentParser(description="Line follower com PID (TCRT5000)")
    parser.add_argument("--seed", type=int, default=7, help="semente da trajetória")
    parser.add_argument("--sensors", type=int, default=None, help="nº de sensores (2, 5 ou 8)")
    parser.add_argument("--regenerate", action="store_true", help="força nova trajetória")
    args = parser.parse_args()

    config = load_config(project_root / "config" / "line_follower.yaml")

    if args.sensors is not None:
        config["robot"]["num_sensors"] = int(args.sensors)

    if args.regenerate or not TRACK_PATH.exists():
        print(f"Gerando trajetória aleatória (seed={args.seed}) -> {TRACK_PATH}")
    points = generate_random_track(TRACK_PATH, seed=args.seed)

    config["world"]["line_map_image"] = str(TRACK_PATH)

    sim = Simulator(config=config, controller=line_pid_controller)

    x0, y0, theta0 = pose_on_track(points)
    sim.robot.set_initial_pose(x0, y0, theta0)
    sim.camera.initial_zoom = 1.0
    sim.camera.reset()

    print(
        f"Robô seguidor de linha: {sim.robot.num_sensors} sensores | "
        f"pose inicial=({x0:.2f}, {y0:.2f}, {math.degrees(theta0):.1f}°) | "
        f"PID kp={config['line_pid']['kp']}, ki={config['line_pid']['ki']}, "
        f"kd={config['line_pid']['kd']}"
    )
    print("Clique em Start (ou pressione Espaço) para iniciar.")

    sim.run()


if __name__ == "__main__":
    main()
