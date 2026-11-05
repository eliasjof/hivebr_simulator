#!/usr/bin/env python3
"""
Script de diagnostico para validar o sensor TCR5000 simulado.
Verifica:
1. Se o mapa de linha tem fundo branco puro (255)
2. Leituras dos sensores em diferentes posicoes
3. Resposta do modelo TCR5000
"""

import sys
from pathlib import Path
import numpy as np
from PIL import Image

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.robots.line_follower import LineFollowerRobot
from hivebr.engine.line_map import LineTrackMap


def check_line_map(image_path: str, resolution: float = 0.005):
    """Verifica a qualidade do mapa de linha."""
    print(f"\n{'='*60}")
    print(f"VERIFICACAO DO MAPA DE LINHA: {image_path}")
    print(f"{'='*60}")
    
    img = Image.open(image_path).convert("L")
    arr = np.array(img, dtype=np.uint8)
    
    print(f"Dimensoes: {arr.shape[1]}x{arr.shape[0]} px")
    print(f"Resolucao: {resolution} m/px")
    print(f"Mundo: {arr.shape[1]*resolution:.2f}m x {arr.shape[0]*resolution:.2f}m")
    
    unique_vals = np.unique(arr)
    print(f"Valores unicos: {len(unique_vals)} ({unique_vals.min()} a {unique_vals.max()})")
    print(f"Valores: {unique_vals[:20]}{'...' if len(unique_vals) > 20 else ''}")
    
    # Verifica se é binário (preto/branco puro)
    if len(unique_vals) == 2 and unique_vals[0] == 0 and unique_vals[1] == 255:
        print("[OK] MAPA BINARIO PERFEITO (apenas 0 e 255)")
    elif unique_vals.min() == 0 and unique_vals.max() == 255:
        print(f"[AVISO] MAPA TEM VALORES INTERMEDIARIOS ({len(unique_vals)} niveis)")
        print("   Isso causa bleeding nos sensores! Considere limiarizar a imagem.")
    else:
        print(f"[ERRO] MAPA PROBLEMATICO: min={unique_vals.min()}, max={unique_vals.max()}")
        print("   O fundo deve ser 255 (branco) e a linha 0 (preto).")
    
    # Estatísticas
    black_pixels = np.sum(arr == 0)
    white_pixels = np.sum(arr == 255)
    other_pixels = arr.size - black_pixels - white_pixels
    print(f"\nPixels pretos (linha): {black_pixels} ({100*black_pixels/arr.size:.1f}%)")
    print(f"Pixels brancos (fundo): {white_pixels} ({100*white_pixels/arr.size:.1f}%)")
    if other_pixels > 0:
        print(f"Pixels cinza (borda/AA): {other_pixels} ({100*other_pixels/arr.size:.1f}%)")
    
    return arr


def test_tcrt5000_response():
    """Testa a curva de resposta do modelo TCR5000."""
    print(f"\n{'='*60}")
    print("TESTE DO MODELO TCR5000")
    print(f"{'='*60}")
    
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
    
    print("\nEscuridao (mapa) -> Resposta TCR5000:")
    print(f"{'Darkness':>10} | {'Response':>10} | {'Expected'}")
    print("-" * 45)
    
    test_points = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for d in test_points:
        r = robot._tcrt5000_response(d)
        expected = "branco/fundo" if d == 0 else "preto/linha" if d == 1 else "transicao"
        print(f"{d:>10.2f} | {r:>10.4f} | {expected}")
    
    print(f"\nRange realistico: [{robot._tcrt5000_response(0):.3f}, {robot._tcrt5000_response(1):.3f}]")
    print("(Nao rail-to-rail: sensor real nao chega a 0V nem Vcc)")


def test_sensor_readings():
    """Testa leituras dos sensores em posicoes conhecidas."""
    print(f"\n{'='*60}")
    print("TESTE DE LEITURAS DOS SENSORES")
    print(f"{'='*60}")
    
    # Carrega config e cria simulador
    config = load_config(project_root / "config" / "line_follower.yaml")
    sim = Simulator(config=config)
    
    line_map = sim.world.line_map
    robot = sim.robot
    
    print(f"\nConfiguracao do robo:")
    print(f"  Sensores: {robot.num_sensors}")
    print(f"  Span: {robot.sensor_span*1000:.1f}mm")
    print(f"  Offset: {robot.sensor_offset*1000:.1f}mm")
    print(f"  Aperture: {robot.sensor_aperture*1000:.1f}mm")
    print(f"  Threshold: {robot.line_threshold}")
    print(f"  Posicoes locais: {robot.sensor_local}")
    
    # Testa em 3 posicoes: sobre a linha, fora da linha, na borda
    # Primeiro, encontra um ponto na linha
    track_path = project_root / "config" / "line_track.png"
    if track_path.exists():
        img = Image.open(track_path).convert("L")
        arr = np.array(img)
        # Encontra pixels pretos
        black_pixels = np.argwhere(arr == 0)
        if len(black_pixels) > 0:
            # Pega um pixel preto no meio
            mid_idx = len(black_pixels) // 2
            py, px = black_pixels[mid_idx]
            # Converte para mundo
            wx = px * config["world"]["resolution"]
            wy = (arr.shape[0] - 1 - py) * config["world"]["resolution"]
            
            print(f"\n--- Posicao 1: CENTRO DA LINHA ({wx:.3f}, {wy:.3f}) ---")
            robot.set_initial_pose(wx, wy, 0.0)
            robot.read_line_sensors(line_map)
            print_sensor_state(robot)
            
            # Posicao 2: Fora da linha (move 10cm para lado)
            print(f"\n--- Posicao 2: FORA DA LINHA ({wx:.3f}, {wy+0.10:.3f}) ---")
            robot.set_initial_pose(wx, wy + 0.10, 0.0)
            robot.read_line_sensors(line_map)
            print_sensor_state(robot)
            
            # Posicao 3: Na borda da linha (move metade da largura)
            print(f"\n--- Posicao 3: BORDA DA LINHA ({wx:.3f}, {wy+0.01:.3f}) ---")
            robot.set_initial_pose(wx, wy + 0.01, 0.0)
            robot.read_line_sensors(line_map)
            print_sensor_state(robot)
        else:
            print("Nenhum pixel preto encontrado no mapa!")
    else:
        print(f"Mapa nao encontrado: {track_path}")


def print_sensor_state(robot):
    """Imprime estado dos sensores formatado."""
    print(f"  Leituras brutas:  [{', '.join(f'{v:.3f}' for v in robot.sensor_readings)}]")
    print(f"  Pesos:            [{', '.join(f'{w:.2f}' for w in robot.sensor_weights)}]")
    print(f"  Line error:       {robot.line_error:.4f}")
    print(f"  Line position:    {robot.line_position*1000:.1f}mm")
    print(f"  Line lost:        {robot.line_lost}")
    print(f"  Last sign:        {robot._last_sign:.1f}")


def test_aperture_effect():
    """Demonstra efeito do aperture na leitura."""
    print(f"\n{'='*60}")
    print("EFEITO DO APERTURE (raio de amostragem)")
    print(f"{'='*60}")
    
    # Cria mapa simples: linha vertical preta no centro
    from hivebr.engine.line_map import LineTrackMap
    import tempfile
    import os
    
    # Imagem 200x200, linha de 4px no centro (x=100)
    img_arr = np.ones((200, 200), dtype=np.uint8) * 255
    img_arr[:, 98:102] = 0  # Linha preta de 4px
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        temp_path = f.name
    Image.fromarray(img_arr).save(temp_path)
    
    try:
        line_map = LineTrackMap(temp_path, resolution=0.005)
        
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
        
        # Testa em x=1.0 (centro da linha), y=0.5
        # Sensores estao em y = +/-span/2
        test_y = 0.5
        line_x = 1.0  # 100px * 0.005 = 0.5m... wait
        
        # Mundo: 200px * 0.005 = 1.0m. Linha em x=100px = 0.5m
        line_x = 0.5
        
        print(f"\nLinha vertical em x={line_x}m. Testando posicoes em y={test_y}m:")
        print(f"{'Pos X':>8} | {'Sensor 0 (dir)':>15} | {'Sensor 2 (centro)':>18} | {'Sensor 4 (esq)':>15} | {'Error':>7} | {'Lost'}")
        print("-" * 95)
        
        for test_x in [0.30, 0.40, 0.45, 0.48, 0.50, 0.52, 0.55, 0.60, 0.70]:
            robot.set_initial_pose(test_x, test_y, 0.0)
            robot.read_line_sensors(line_map)
            s = robot.sensor_readings
            print(f"{test_x:>8.2f} | {s[0]:>15.3f} | {s[2]:>18.3f} | {s[4]:>15.3f} | {robot.line_error:>7.3f} | {robot.line_lost}")
    
    finally:
        os.unlink(temp_path)


if __name__ == "__main__":
    print("DIAGNOSTICO DO SENSOR TCR5000 - HIVEBR SIMULATOR")
    print("=" * 60)
    
    # 1. Verifica mapa de linha
    track_path = project_root / "config" / "line_track.png"
    if track_path.exists():
        check_line_map(str(track_path), resolution=0.005)
    else:
        print(f"\n[AVISO] Mapa nao encontrado: {track_path}")
        print("   Execute examples/line_follower.py para gerar.")
    
    # 2. Testa modelo TCR5000
    test_tcrt5000_response()
    
    # 3. Testa leituras reais
    test_sensor_readings()
    
    # 4. Demonstra efeito do aperture
    test_aperture_effect()
    
    print(f"\n{'='*60}")
    print("DIAGNOSTICO CONCLUIDO")
    print(f"{'='*60}")