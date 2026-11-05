#!/usr/bin/env python3
"""
Teste headless (sem GUI) do sensor TCR5000 melhorado.
"""

import sys
from pathlib import Path
import numpy as np

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.robots.line_follower import LineFollowerRobot, pose_on_track, generate_random_track
from hivebr.engine.line_map import LineTrackMap

TRACK_PATH = project_root / "config" / "line_track.png"


def test_sensor_model():
    """Testa o modelo TCR5000 isoladamente."""
    print("=" * 60)
    print("TESTE 1: Modelo TCR5000")
    print("=" * 60)
    
    robot = LineFollowerRobot({"robot": {
        "length": 0.10, "width": 0.10, "radius": 0.05,
        "num_sensors": 5, "sensor_offset": 0.05,
        "line_width": 0.02, "sensor_aperture": 0.002,
        "sensor_noise": 0.0, "line_threshold": 0.35,
        "max_speed": 0.6, "max_omega": 3.5
    }, "colors": {
        "robot": [0, 100, 255],
        "silver": [192, 192, 186]
    }})
    
    print("\nResposta do TCR5000 (darkness -> voltage):")
    print(f"{'Darkness':>10} | {'Voltage':>8} | {'Above Thr?':>10}")
    print("-" * 38)
    
    for d in [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]:
        v = robot._tcrt5000_response(d)
        above = "SIM" if v > robot.line_threshold else "NAO"
        print(f"{d:>10.1f} | {v:>8.4f} | {above:>10}")
    
    print(f"\nThreshold: {robot.line_threshold}")
    print(f"Branco (0.0) -> {robot._tcrt5000_response(0):.4f} {'(abaixo do thr)' if robot._tcrt5000_response(0) < robot.line_threshold else '(ACIMA DO THR - PROBLEMA!)'}")
    print(f"Preto (1.0) -> {robot._tcrt5000_response(1):.4f} {'(acima do thr)' if robot._tcrt5000_response(1) > robot.line_threshold else '(ABAIXO DO THR - PROBLEMA!)'}")


def test_line_map_sampling():
    """Testa amostragem do mapa de linha."""
    print("\n" + "=" * 60)
    print("TESTE 2: Amostragem do Mapa de Linha")
    print("=" * 60)
    
    # Cria mapa de teste: linha vertical preta no centro
    img_arr = np.ones((400, 400), dtype=np.uint8) * 255
    # Linha de 4 pixels = 2cm em 0.005m/px
    img_arr[:, 198:202] = 0
    
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name
    from PIL import Image
    Image.fromarray(img_arr).save(temp_path)
    
    try:
        line_map = LineTrackMap(temp_path, resolution=0.005)
        
        print(f"Mapa: {line_map.width}x{line_map.height} px, {line_map.width_m:.2f}x{line_map.height_m:.2f}m")
        print(f"Linha em x = 198-201 px = {198*0.005:.3f}-{201*0.005:.3f}m")
        
        robot = LineFollowerRobot({"robot": {
            "length": 0.10, "width": 0.10, "radius": 0.05,
            "num_sensors": 5, "sensor_offset": 0.05,
            "line_width": 0.02, "sensor_aperture": 0.002,
            "sensor_noise": 0.0, "line_threshold": 0.35,
            "max_speed": 0.6, "max_omega": 3.5
        }, "colors": {
            "robot": [0, 100, 255],
            "silver": [192, 192, 186]
        }})
        
        # Testa posições variando x (perpendicular à linha)
        # Robô em y=1.0m (meio do mundo), theta=0
        # Sensores em x = robot.x + 0.05 (sensor_offset)
        test_y = 1.0
        
        print(f"\nRobô em y={test_y}m, theta=0. Sensor offset=0.05m.")
        print(f"{'Robot X':>8} | {'Sens X':>8} | {'S0':>6} {'S1':>6} {'S2':>6} {'S3':>6} {'S4':>6} | {'Error':>7} | {'Lost'}")
        print("-" * 85)
        
        for robot_x in [0.30, 0.35, 0.40, 0.43, 0.45, 0.47, 0.49, 0.50, 0.51, 0.53, 0.55, 0.60]:
            robot.set_initial_pose(robot_x, test_y, 0.0)
            robot.read_line_sensors(line_map)
            s = robot.sensor_readings
            sensor_x = robot_x + robot.sensor_offset
            print(f"{robot_x:>8.2f} | {sensor_x:>8.3f} | {s[0]:>6.3f} {s[1]:>6.3f} {s[2]:>6.3f} {s[3]:>6.3f} {s[4]:>6.3f} | {robot.line_error:>+7.3f} | {robot.line_lost}")
    
    finally:
        os.unlink(temp_path)


def test_real_track():
    """Testa na pista real gerada."""
    print("\n" + "=" * 60)
    print("TESTE 3: Pista Real (line_track.png)")
    print("=" * 60)
    
    if not TRACK_PATH.exists():
        print("Gerando pista...")
        points = generate_random_track(TRACK_PATH, seed=7)
    else:
        points = generate_random_track(TRACK_PATH, seed=7)
    
    config = load_config(project_root / "config" / "line_follower.yaml")
    config["world"]["line_map_image"] = str(TRACK_PATH)
    sim = Simulator(config=config)
    
    line_map = sim.world.line_map
    robot = sim.robot
    
    print(f"Mapa: {line_map.width}x{line_map.height} px, {line_map.width_m:.2f}x{line_map.height_m:.2f}m")
    print(f"Robô: {robot.num_sensors} sensores, offset={robot.sensor_offset*1000:.0f}mm, span={robot.sensor_span*1000:.0f}mm")
    print(f"Aperture: {robot.sensor_aperture*1000:.1f}mm, Threshold: {robot.line_threshold}")
    
    # Testa em vários pontos da pista
    print(f"\nTestando em pontos da pista (sensores posicionados na linha):")
    print(f"{'Idx':>4} | {'Robot X':>8} {'Robot Y':>8} | {'S0':>6} {'S1':>6} {'S2':>6} {'S3':>6} {'S4':>6} | {'Error':>7} | {'Lost'}")
    print("-" * 95)
    
    for idx in [0, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
        if idx >= len(points):
            continue
        x0, y0, theta0 = pose_on_track(points, index=idx, lookahead=5)
        # Posiciona centro do robô para que sensores fiquem no ponto da pista
        offset = robot.sensor_offset
        robot_x = x0 - offset * np.cos(theta0)
        robot_y = y0 - offset * np.sin(theta0)
        robot.set_initial_pose(robot_x, robot_y, theta0)
        robot.read_line_sensors(line_map)
        s = robot.sensor_readings
        print(f"{idx:>4} | {robot_x:>8.3f} {robot_y:>8.3f} | {s[0]:>6.3f} {s[1]:>6.3f} {s[2]:>6.3f} {s[3]:>6.3f} {s[4]:>6.3f} | {robot.line_error:>+7.3f} | {robot.line_lost}")
    
    # Testa FORA da linha (move 10cm perpendicular)
    print(f"\nTestando FORA da linha (deslocado 10cm perpendicular):")
    idx = 100
    x0, y0, theta0 = pose_on_track(points, index=idx, lookahead=5)
    offset = robot.sensor_offset
    robot_x = x0 - offset * np.cos(theta0)
    robot_y = y0 - offset * np.sin(theta0)
    
    # Vetor perpendicular (esquerda do robô)
    perp_x = -np.sin(theta0)
    perp_y = np.cos(theta0)
    
    for dist in [0.0, 0.02, 0.05, 0.10, 0.15]:
        test_x = robot_x + dist * perp_x
        test_y = robot_y + dist * perp_y
        robot.set_initial_pose(test_x, test_y, theta0)
        robot.read_line_sensors(line_map)
        s = robot.sensor_readings
        print(f"  Dist {dist*1000:>4.0f}mm: [{', '.join(f'{v:.3f}' for v in s)}] | Error={robot.line_error:+.3f} | Lost={robot.line_lost}")


def test_noise_effect():
    """Testa efeito do ruído."""
    print("\n" + "=" * 60)
    print("TESTE 4: Efeito do Ruído (sensor_noise=0.01)")
    print("=" * 60)
    
    # Mapa simples
    img_arr = np.ones((200, 200), dtype=np.uint8) * 255
    img_arr[:, 98:102] = 0
    import tempfile, os
    from PIL import Image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name
    Image.fromarray(img_arr).save(temp_path)
    
    try:
        line_map = LineTrackMap(temp_path, resolution=0.005)
        
        robot = LineFollowerRobot({"robot": {
            "length": 0.10, "width": 0.10, "radius": 0.05,
            "num_sensors": 5, "sensor_offset": 0.05,
            "line_width": 0.02, "sensor_aperture": 0.002,
            "sensor_noise": 0.01, "line_threshold": 0.35,
            "max_speed": 0.6, "max_omega": 3.5
        }, "colors": {
            "robot": [0, 100, 255],
            "silver": [192, 192, 186]
        }})
        
        robot.set_initial_pose(0.45, 0.5, 0.0)  # Sensores na linha (x=0.5)
        
        print("Leituras com ruído (10 amostras na linha):")
        for i in range(10):
            robot.read_line_sensors(line_map)
            s = robot.sensor_readings
            print(f"  {i+1}: [{', '.join(f'{v:.3f}' for v in s)}] | Error={robot.line_error:+.3f} | Lost={robot.line_lost}")
        
        robot.set_initial_pose(0.60, 0.5, 0.0)  # Sensores fora da linha
        
        print("\nLeituras com ruído (10 amostras FORA da linha):")
        for i in range(10):
            robot.read_line_sensors(line_map)
            s = robot.sensor_readings
            print(f"  {i+1}: [{', '.join(f'{v:.3f}' for v in s)}] | Error={robot.line_error:+.3f} | Lost={robot.line_lost}")
    
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    print("TESTES HEADLESS DO SENSOR TCR5000 MELHORADO")
    print("=" * 60)
    
    test_sensor_model()
    test_line_map_sampling()
    test_real_track()
    test_noise_effect()
    
    print("\n" + "=" * 60)
    print("TODOS OS TESTES CONCLUIDOS")
    print("=" * 60)