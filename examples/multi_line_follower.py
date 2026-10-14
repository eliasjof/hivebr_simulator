"""Vários robôs seguidores de linha na MESMA pista, iniciando no MESMO ponto.

Cada B-bot usa um conjunto de ganhos PID diferente, o que permite comparar
o desempenho (tempo por volta, tempo total, número de voltas) de estratégias
de sintonia distintas sob condições idênticas.

Como todos os robôs partem exatamente do mesmo ponto, a colisão robô-robô é
desativada através de::

    config["interaction"] = {
        "collision_policy": "none",   # ou robot_collision: False
        "robot_collision": False,
    }

O tempo de cada robô aparece no painel de informações. Use o botão
"Toggle Times" (ou ``config["show_times"]``) para desabilitar essa
visualização.

Controles padrão do simulador:
    Espaço (botão Start) -> inicia/pausa a simulação
    Botão do meio        -> arrastar (pan) | roda do mouse -> zoom
    Botão Toggle Times   -> mostra/esconde o tempo por robô

Referência de geração de pista: ``examples/line_follower.py``.
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.geometry import clamp

from line_follower import (
    generate_random_track,
    pose_on_track,
)

TRACK_PATH = project_root / "config" / "line_track.png"

# ---------------------------------------------------------------------------
# Conjuntos de ganhos PID avaliados (um por robô)
# ---------------------------------------------------------------------------
GAIN_SETS = [
    {"base_speed": 0.30, "kp": 3.0, "ki": 0.00, "kd": 0.6, "integral_limit": 1.0},
    {"base_speed": 0.30, "kp": 10.0, "ki": 0.00, "kd": 0.0, "integral_limit": 1.0},
    {"base_speed": 0.30, "kp": 6.0, "ki": 0.00, "kd": 0.0, "integral_limit": 1.0},
    {"base_speed": 0.30, "kp": 28.0, "ki": 0.20, "kd": 1.6, "integral_limit": 1.0},
]

# Estado do termo integral por robô (chave = id(robot)).
_CTRL_STATE: dict[int, dict] = {}


def line_pid_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    """PID de seguimento de linha com ganhos POR ROBÔ.

    Os ganhos vêm de ``robot.pid_params`` (definido no ``main``). Se ausente,
    usa o bloco ``line_pid`` da configuração global.
    """
    line_map = getattr(world, "line_map", None)
    if line_map is None or not hasattr(robot, "read_line_sensors"):
        return {"v": 0.0, "omega": 0.0}

    robot.read_line_sensors(line_map)
    error = robot.line_error

    pid = getattr(robot, "pid_params", None) or cfg.get("line_pid", {})
    base_speed = float(pid.get("base_speed", 0.35))
    kp = float(pid.get("kp", 3.0))
    ki = float(pid.get("ki", 0.0))
    kd = float(pid.get("kd", 0.8))
    integral_limit = float(pid.get("integral_limit", 1.0))

    state = _CTRL_STATE.setdefault(id(robot), {"integral": 0.0, "prev": 0.0})

    if robot.line_lost:
        state["integral"] = 0.0
        omega = 1.5 * (1.0 if error >= 0.0 else -1.0)
        velocity = base_speed * 0.4
    else:
        state["integral"] = clamp(
            state["integral"] + error * dt, -integral_limit, integral_limit
        )
        derivative = (error - state["prev"]) / dt if dt > 0.0 else 0.0
        omega = kp * error + ki * state["integral"] + kd * derivative
        velocity = base_speed * max(0.15, 1.0 - 0.6 * abs(error))

    state["prev"] = error

    velocity = clamp(velocity, 0.0, robot.max_speed)
    omega = clamp(omega, -robot.max_omega, robot.max_omega)
    return {"v": velocity, "omega": omega}


def resolve_gains(num_robots: int):
    """Repete/corta a lista de ganhos para o número de robôs pedido."""
    if num_robots <= len(GAIN_SETS):
        return GAIN_SETS[:num_robots]
    gains = []
    while len(gains) < num_robots:
        gains.append(GAIN_SETS[len(gains) % len(GAIN_SETS)])
    return gains


def main():
    parser = argparse.ArgumentParser(
        description="Multi line follower: mesma pista, mesmo ponto, ganhos diferentes"
    )
    parser.add_argument("--seed", type=int, default=7, help="semente da trajetória")
    parser.add_argument("--sensors", type=int, default=None, help="nº de sensores (2, 5 ou 8)")
    parser.add_argument("--robots", type=int, default=len(GAIN_SETS), help="número de robôs")
    parser.add_argument(
        "--spread",
        type=float,
        default=0.0,
        help="deslocamento lateral (m) entre robôs; 0 = todos no mesmo ponto",
    )
    parser.add_argument("--regenerate", action="store_true", help="força nova trajetória")
    args = parser.parse_args()

    num_robots = max(1, int(args.robots))
    gains = resolve_gains(num_robots)

    config = load_config(project_root / "config" / "line_follower.yaml")
    if args.sensors is not None:
        config["robot"]["num_sensors"] = int(args.sensors)

    if args.regenerate or not TRACK_PATH.exists():
        print(f"Gerando trajetória aleatória (seed={args.seed}) -> {TRACK_PATH}")
    points = generate_random_track(TRACK_PATH, seed=args.seed)
    config["world"]["line_map_image"] = str(TRACK_PATH)

    # Todos os robôs partem do MESMO ponto/tangente da pista.
    x0, y0, theta0 = pose_on_track(points)
    config["robots"] = [
        {
            "id": i,
            "type": "line_follower",
            "initial_pose": [x0, y0, theta0],
            "radius": float(config["robot"].get("radius", 0.05)),
        }
        for i in range(num_robots)
    ]

    # Não avaliar colisão entre os robôs (eles começam sobrepostos).
    config["interaction"] = {
        "collision_policy": "none",
        "robot_collision": False,
        "robot_safety_margin": 0.0,
        "resolve_push": 0.0,
        "comm_radius": None,
        "show_robot_links": False,
    }

    # Visualização do tempo por robô (botão "Toggle Times" no painel).
    config["show_times"] = True

    sim = Simulator(config=config, controller=line_pid_controller)

    # Associa os ganhos a cada robô e, opcionalmente, aplica um leve
    # deslocamento lateral para facilitar a visualização das trajetórias.
    lateral = np.array([-math.sin(theta0), math.cos(theta0)])
    for i, robot in enumerate(sim.robots):
        robot.pid_params = dict(gains[i])
        if args.spread > 0.0:
            offset = (i - (num_robots - 1) / 2.0) * args.spread
            robot.set_initial_pose(x0 + lateral[0] * offset, y0 + lateral[1] * offset, theta0)

    sim.camera.initial_zoom = 1.0
    sim.camera.reset()

    print(
        f"{num_robots} robôs seguidores de linha | {sim.robots[0].num_sensors} sensores | "
        f"ponto inicial=({x0:.2f}, {y0:.2f}, {math.degrees(theta0):.1f}°) | "
        f"colisão robô-robô: DESATIVADA"
    )
    for i, g in enumerate(gains):
        print(
            f"  B-Bot{i}: kp={g['kp']:.2f}, ki={g['ki']:.2f}, kd={g['kd']:.2f}, "
            f"v0={g['base_speed']:.2f}"
        )
    print("Clique em Start (ou pressione Espaço) para iniciar.")

    sim.run()

    print("\n===== Resultado por robô =====")
    for i, robot in enumerate(sim.robots):
        g = gains[i]
        stats = robot.lap_statistics()
        tag = f"B-Bot{i} (kp={g['kp']:.2f}, ki={g['ki']:.2f}, kd={g['kd']:.2f})"
        if stats["count"]:
            print(
                f"{tag}: {stats['count']} volta(s) | média={stats['mean']:.2f}s | "
                f"melhor={stats['best']:.2f}s | pior={stats['worst']:.2f}s"
            )
        elif getattr(robot, "finished", False):
            print(f"{tag}: percurso concluído em {robot.finish_time:.2f}s.")
        else:
            print(f"{tag}: encerrado em {robot.time:.2f}s sem voltas completas.")


if __name__ == "__main__":
    main()
