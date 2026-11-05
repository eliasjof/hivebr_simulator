#!/usr/bin/env python3
"""
Testa múltiplas seeds para encontrar uma pista navegável.
"""

import sys
from pathlib import Path
import numpy as np

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.robots.line_follower import LineFollowerRobot, pose_on_track, generate_random_track

TRACK_PATH = project_root / "config" / "line_track.png"


def line_pid_controller(robot, world, goal, cfg, dt, lidar_readings=None):
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

    if not hasattr(robot, '_pid_state'):
        robot._pid_state = {"integral": 0.0, "prev": 0.0}
    state = robot._pid_state

    if robot.line_lost:
        state["integral"] = 0.0
        omega = 1.5 * (1.0 if error >= 0.0 else -1.0)
        velocity = base_speed * 0.4
    else:
        state["integral"] = np.clip(state["integral"] + error * dt, -integral_limit, integral_limit)
        derivative = (error - state["prev"]) / dt if dt > 0.0 else 0.0
        omega = kp * error + ki * state["integral"] + kd * derivative
        velocity = base_speed * max(0.15, 1.0 - 0.6 * abs(error))

    state["prev"] = error
    velocity = np.clip(velocity, 0.0, robot.max_speed)
    omega = np.clip(omega, -robot.max_omega, robot.max_omega)
    return {"v": velocity, "omega": omega}


def test_seed(seed):
    print(f"\n=== Testando seed={seed} ===")
    
    config = load_config(project_root / "config" / "line_follower.yaml")
    
    points = generate_random_track(TRACK_PATH, seed=seed)
    config["world"]["line_map_image"] = str(TRACK_PATH)
    
    sim = Simulator(config=config, controller=line_pid_controller)
    
    x0, y0, theta0 = pose_on_track(points, index=100, lookahead=5)
    offset = config["robot"]["sensor_offset"]
    x0 -= offset * np.cos(theta0)
    y0 -= offset * np.sin(theta0)
    
    sim.robot.set_initial_pose(x0, y0, theta0)
    
    dt = 1.0 / 60.0
    max_steps = 3600  # 60 segundos
    
    for step in range(max_steps):
        cmd = line_pid_controller(sim.robot, sim.world, None, config, dt)
        sim.robot.step(cmd, dt)
        sim.robot.time += dt
        
        if sim.robot.finished:
            print(f"  [OK] VOLTA COMPLETA em {sim.robot.finish_time:.2f}s!")
            return True
        if sim.robot.line_lost and hasattr(sim.robot, '_lost_time') and sim.robot._lost_time > sim.robot.lost_timeout:
            print(f"  [FAIL] Linha perdida (timeout)")
            return False
    
    print(f"  [TIME] Sem volta em 60s (dist={sim.robot.distance_traveled:.1f}m)")
    return False


if __name__ == "__main__":
    print("BUSCANDO SEED COM PISTA NAVEGÁVEL")
    print("=" * 50)
    
    for seed in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 42, 100]:
        test_seed(seed)
    
    print("\nFim.")