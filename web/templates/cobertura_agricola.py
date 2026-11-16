"""Atividade: cobertura de uma area agricola em zigue-zague.

O robo deve varrer o campo retangular de (2, 2) a (18, 10) em faixas paralelas.
Complete gerar_cobertura(): comece em um canto, va ate o outro lado, desca uma
faixa e volte na direcao oposta (boustrophedon).

O console mostra o numero de waypoints gerados.
"""

import math

from hivebr.engine import Simulator, load_config

X0, X1 = 2.0, 18.0
Y0, Y1 = 2.0, 10.0
ESPACAMENTO = 2.0
VMAX = 1.2
KP_DIST = 1.5
KP_ANG = 4.0


def gerar_cobertura(largura, altura, espacamento):
    """Waypoints (x, y) que cobrem o retangulo em zigue-zague."""
    # TODO: percorra as faixas em y e alterne o sentido em x.
    raise NotImplementedError


def normaliza(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controlador(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}
    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    dist = math.hypot(dx, dy)
    if dist < 0.10:
        return {"v": 0.0, "omega": 0.0}
    ang = normaliza(math.atan2(dy, dx) - robot.theta)
    v = min(VMAX, KP_DIST * dist) * max(0.0, math.cos(ang))
    omega = max(-robot.max_omega, min(robot.max_omega, KP_ANG * ang))
    return {"v": v, "omega": omega}


def rodar(sim, limite=180.0):
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    caminho = gerar_cobertura(X1 - X0, Y1 - Y0, ESPACAMENTO)
    if not caminho:
        caminho = [(X0, Y0)]

    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["obstacles"] = []
    config["robot"]["initial_pose"] = [caminho[0][0], caminho[0][1], 0.0]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador)
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in caminho])

    print(f"Waypoints: {len(caminho)}")
    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulacao encerrada.")
