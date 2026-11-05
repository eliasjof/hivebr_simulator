#!/usr/bin/env python3
"""
Teste headless do controlador PID com o sensor TCR5000 melhorado.
Simula alguns segundos sem GUI.
"""

import sys
from pathlib import Path
import numpy as np

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.robots.line_follower import LineFollowerRobot, pose_on_track, generate_random_track
from hivebr.engine.world import World

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
    print("TESTE HEADLESS DO CONTROLADOR PID + TCR5000")
    print("=" * 60)
    
    config = load_config(project_root / "config" / "line_follower.yaml")
    
    if not TRACK_PATH.exists():
        print("Gerando pista...")
        points = generate_random_track(TRACK_PATH, seed=7)
    else:
        points = generate_random_track(TRACK_PATH, seed=7)
    
    config["world"]["line_map_image"] = str(TRACK_PATH)
    
    # Cria mundo e robô sem GUI
    from hivebr.engine.simulator import Simulator
    sim = Simulator(config=config, controller=line_pid_controller)
    
    x0, y0, theta0 = pose_on_track(points, index=100, lookahead=5)
    offset = config["robot"]["sensor_offset"]
    x0 -= offset * np.cos(theta0)
    y0 -= offset * np.sin(theta0)
    
    sim.robot.set_initial_pose(x0, y0, theta0)
    
    print(f"Posição inicial: ({x0:.3f}, {y0:.3f}, {np.degrees(theta0):.1f}deg)")
    print(f"Sensores: {sim.robot.num_sensors}, offset={sim.robot.sensor_offset*1000:.0f}mm")
    print(f"Threshold: {sim.robot.line_threshold}, noise: {sim.robot.sensor_noise}")
    print()
    
    # Simula por 30 segundos (1800 steps a 60Hz = 30s)
    dt = 1.0 / 60.0
    max_steps = 1800
    
    print("Simulando...")
    print(f"{'Step':>5} | {'Time':>5} | {'Pos':>18} | {'Theta':>6} | {'v':>5} {'w':>6} | {'Sensors':>35} | {'Err':>6} | {'Lost'}")
    print("-" * 110)
    
    for step in range(max_steps):
        # Executa o controlador
        cmd = line_pid_controller(sim.robot, sim.world, None, config, dt)
        # Step do robô
        sim.robot.step(cmd, dt)
        sim.robot.time += dt
        
        # Lê sensores para debug
        sim.robot.read_line_sensors(sim.world.line_map)
        
        if step % 120 == 0:  # A cada 2 segundos
            r = sim.robot
            s_str = ', '.join(f'{v:.2f}' for v in r.sensor_readings)
            print(f"{step:>5} | {r.time:>5.1f} | ({r.x:>6.2f},{r.y:>6.2f}) | {np.degrees(r.theta):>+6.0f} | "
                  f"{r.v:>5.2f} {r.omega:>+6.2f} | [{s_str}] | {r.line_error:>+6.2f} | {r.line_lost}")
        
        # Verifica se completou volta ou perdeu linha por muito tempo
        if r.finished:
            print(f"\nPercurso concluído em {r.finish_time:.2f}s!")
            break
        if r.line_lost and hasattr(r, '_lost_time') and r._lost_time > r.lost_timeout:
            print(f"\nLinha perdida por {r.lost_timeout}s - fim de pista")
            break
    
    stats = sim.robot.lap_statistics()
    if stats["count"] > 0:
        print(f"\nVoltas completadas: {stats['count']}")
        print(f"Tempos: {[f'{t:.2f}s' for t in sim.robot.lap_times]}")
        print(f"Média: {stats['mean']:.2f}s, Melhor: {stats['best']:.2f}s")
    else:
        print(f"\nNenhuma volta completa. Distância: {sim.robot.distance_traveled:.2f}m")


if __name__ == "__main__":
    main()