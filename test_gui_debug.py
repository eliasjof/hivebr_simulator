#!/usr/bin/env python3
"""
Teste do seguidor de linha com debug das leituras dos sensores.
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
    """Controlador PID que segue a linha usando apenas os sensores de linha."""
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


def main():
    print("TESTE GUI DO SEGUIDOR DE LINHA COM DEBUG")
    print("=" * 60)
    
    config = load_config(project_root / "config" / "line_follower.yaml")
    config["window"]["width"] = 1000
    config["window"]["height"] = 700
    
    if not TRACK_PATH.exists():
        print("Gerando pista...")
        points = generate_random_track(TRACK_PATH, seed=7)
    else:
        points = generate_random_track(TRACK_PATH, seed=7)
    
    config["world"]["line_map_image"] = str(TRACK_PATH)
    
    sim = Simulator(config=config, controller=line_pid_controller)
    
    x0, y0, theta0 = pose_on_track(points, index=100, lookahead=5)
    offset = config["robot"]["sensor_offset"]
    x0 -= offset * np.cos(theta0)
    y0 -= offset * np.sin(theta0)
    
    sim.robot.set_initial_pose(x0, y0, theta0)
    sim.camera.initial_zoom = 1.0
    sim.camera.reset()
    
    print(f"Posição inicial: ({x0:.3f}, {y0:.3f}, {np.degrees(theta0):.1f}°)")
    print()
    
    # Debug: override step para imprimir sensores
    original_step = sim.robot.step
    step_count = [0]
    
    def debug_step(command, dt):
        original_step(command, dt)
        step_count[0] += 1
        if step_count[0] % 120 == 0:  # A cada ~2s
            sim.robot.read_line_sensors(sim.world.line_map)
            r = sim.robot
            print(f"t={r.time:.1f}s pos=({r.x:.2f},{r.y:.2f}) theta={np.degrees(r.theta):.0f}deg "
                  f"v={r.v:.2f} w={r.omega:.2f} "
                  f"sensors=[{', '.join(f'{v:.2f}' for v in r.sensor_readings)}] "
                  f"err={r.line_error:+.2f} lost={r.line_lost}")
    
    sim.robot.step = debug_step
    
    print("Iniciando... (ESC para sair)")
    print()
    try:
        sim.run()
    except KeyboardInterrupt:
        pass
    
    print(f"\nFim. Voltas: {sim.robot.lap_statistics()['count']}")


if __name__ == "__main__":
    main()