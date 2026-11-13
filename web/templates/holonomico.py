"""Robô holonômico hexagonal: um B-bot que anda em qualquer direção sem girar.

O modelo 'hexagonal_holonomic' tem três rodas omnidirecionais a 120° e usa as
equações de cinemática do simulador original: o comando {"vx", "vy"} é
convertido nas velocidades das três rodas pela cinemática inversa, respeitando
o limite de velocidade das rodas.

Ele pode andar de lado ou para trás sem virar primeiro.

Aqui o controlador é uma força em direção ao waypoint atual, limitada em
velocidade. O Simulator chama a função a cada passo com o robô, o alvo e a
configuração, e usa o dicionário devolvido como comando.

Como usar: a simulação inicia sozinha. O robô percorre um retângulo na arena.
"""

import math

from hivebr.engine import Simulator, load_config

# Retângulo percorrido pelo robô: pontos (x, y) em metros.
ROTA = [(4.0, 3.0), (16.0, 3.0), (16.0, 9.0), (4.0, 9.0)]
GANHO = 1.2               # m/s de velocidade por metro até o alvo
VELOCIDADE_MAXIMA = 1.5   # m/s
TOLERANCIA = 0.1          # m; abaixo disso o waypoint é considerado atingido


def controlador_holonomico(robot, world, goal, cfg, dt, lidar_readings=None):
    """Devolve {"vx", "vy"}: velocidade nos eixos x e y do mundo."""
    if goal is None:  # rota terminada
        return {"vx": 0.0, "vy": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    if math.hypot(dx, dy) < TOLERANCIA:
        return {"vx": 0.0, "vy": 0.0}

    vx = GANHO * dx
    vy = GANHO * dy
    # Se a velocidade total passar do limite, reduz os dois eixos na mesma proporção.
    total = math.hypot(vx, vy)
    if total > VELOCIDADE_MAXIMA:
        vx *= VELOCIDADE_MAXIMA / total
        vy *= VELOCIDADE_MAXIMA / total
    return {"vx": vx, "vy": vy}


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["robot"].update({
        "type": "hexagonal_holonomic",   # 3 rodas omnidirecionais a 120°
        "initial_pose": [4.0, 3.0, 0.0],
        "radius": 0.3,                   # L: distância do centro até a roda
        "wheel_radius": 0.05,            # r: raio da roda
        "max_wheel_speed": 20.0,         # rad/s
    })

    sim = Simulator(config=config, controller=controlador_holonomico)

    # Cada waypoint é (x, y, theta). O robô holonômico não tem orientação
    # final a alcançar, por isso theta é nan (não desenha a seta).
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in ROTA])

    print("Robô holonômico (hexagonal).")
    sim.run()
    print("Simulação encerrada.")
