#!/usr/bin/env python3
"""
Teste simples do seguidor de linha com as melhorias do TCR5000.
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

    # Estado do PID persistente
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
    print("TESTE DO SEGUIDOR DE LINHA COM TCR5000 MELHORADO")
    print("=" * 60)
    
    # Carrega config
    config = load_config(project_root / "config" / "line_follower.yaml")
    
    # Reduz tamanho da janela para evitar problemas de memória
    config["window"]["width"] = 1000
    config["window"]["height"] = 700
    
    # Gera pista se não existe
    if not TRACK_PATH.exists():
        print("Gerando pista...")
        points = generate_random_track(TRACK_PATH, seed=7)
    else:
        # Usa o gerador para ter pontos contínuos
        points = generate_random_track(TRACK_PATH, seed=7)
    
    config["world"]["line_map_image"] = str(TRACK_PATH)
    
    sim = Simulator(config=config, controller=line_pid_controller)
    
    # Encontra ponto na linha e orienta robô para que SENSORES fiquem na linha
    # O robô tem sensor_offset=0.05m à frente. Precisamos posicionar o centro
    # 5cm ANTES do ponto da linha, na direção oposta à tangente.
    x0, y0, theta0 = pose_on_track(points, index=100, lookahead=5)
    # Move o centro do robô para trás (oposto à direção dos sensores)
    # Sensores estão em sensor_offset à frente. Para ter sensores no ponto (x0,y0),
    # o centro deve estar em (x0 - offset*cos, y0 - offset*sin)
    offset = config["robot"]["sensor_offset"]
    x0 -= offset * np.cos(theta0)
    y0 -= offset * np.sin(theta0)
    
    sim.robot.set_initial_pose(x0, y0, theta0)
    sim.camera.initial_zoom = 1.0
    sim.camera.reset()
    
    print(f"Posição inicial: ({x0:.3f}, {y0:.3f}, {np.degrees(theta0):.1f}°)")
    print(f"Sensores: {sim.robot.num_sensors}")
    print(f"Sensor offset: {sim.robot.sensor_offset*1000:.0f}mm")
    print(f"Sensor span: {sim.robot.sensor_span*1000:.0f}mm")
    print(f"Sensor aperture: {sim.robot.sensor_aperture*1000:.1f}mm")
    print(f"Line threshold: {sim.robot.line_threshold}")
    print(f"Sensor noise: {sim.robot.sensor_noise}")
    print()
    print("Iniciando simulação... (Pressione ESPAÇO para pausar, ESC para sair)")
    print("Observe os valores dos sensores no console abaixo:")
    print()
    
    # Adiciona callback para debug
    original_step = sim.robot.step
    step_count = [0]
    
    def debug_step(command, dt):
        original_step(command, dt)
        step_count[0] += 1
        if step_count[0] % 60 == 0:  # A cada ~1 segundo (60 FPS)
            sim.robot.read_line_sensors(sim.world.line_map)
            readings = sim.robot.sensor_readings
            print(f"  t={sim.robot.time:.1f}s | Sensores: [{', '.join(f'{r:.3f}' for r in readings)}] | "
                  f"Error: {sim.robot.line_error:+.3f} | Lost: {sim.robot.line_lost}")
    
    sim.robot.step = debug_step
    
    try:
        sim.run()
    except KeyboardInterrupt:
        pass
    
    print("\nSimulação encerrada.")
    stats = sim.robot.lap_statistics()
    if stats["count"]:
        print(f"Voltas: {stats['count']} | Média: {stats['mean']:.2f}s | Melhor: {stats['best']:.2f}s")
    elif getattr(sim.robot, "finished", False):
        print(f"Percurso concluído em {sim.robot.finish_time:.2f}s.")


if __name__ == "__main__":
    main()