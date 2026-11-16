"""Atividade: replanejar a rota quando um obstaculo aparece.

O robo segue em linha reta de (2, 2) ate (18, 9). Perto de x = 8 surge uma
caixa no meio do caminho. Complete replanejar(): marque a celula bloqueada na
grade e use buscar() para calcular um desvio.

O console deve mostrar replanejado=<numero de celulas>.
"""

import heapq
import math

import numpy as np

from hivebr.engine import Simulator, load_config

LARGURA, ALTURA = 20.0, 12.0
RESOLUCAO = 0.5
INICIO = (2.0, 2.0)
ALVO = (18.0, 9.0)
BLOQUEIO = (10.0, 5.5, 0.6)
RAIO_ROBO = 0.2
MARGEM = 0.45

VMAX = 1.2
KP_DIST = 1.5
KP_ANG = 4.0

ESTADO = {"sim": None, "grade": None, "objetivo": None, "replanejado": False}


def celula(ponto):
    return (int(ponto[0] / RESOLUCAO), int(ponto[1] / RESOLUCAO))


def centro(celula_):
    return ((celula_[0] + 0.5) * RESOLUCAO, (celula_[1] + 0.5) * RESOLUCAO)


def vizinhos(celula_, grade):
    x, y = celula_
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
        nx, ny = x + dx, y + dy
        if 0 <= nx < grade.shape[0] and 0 <= ny < grade.shape[1] and not grade[nx, ny]:
            yield (nx, ny)


def buscar(grade, inicio, objetivo):
    """A* completo: devolve a lista de celulas do inicio ao objetivo."""
    aberto = [(0.0, inicio)]
    g = {inicio: 0.0}
    pais = {inicio: None}
    fechado = set()
    while aberto:
        _, atual = heapq.heappop(aberto)
        if atual in fechado:
            continue
        if atual == objetivo:
            caminho = []
            while atual is not None:
                caminho.append(atual)
                atual = pais[atual]
            return caminho[::-1]
        fechado.add(atual)
        for vizinho in vizinhos(atual, grade):
            passo = math.hypot(vizinho[0] - atual[0], vizinho[1] - atual[1])
            novo = g[atual] + passo
            if vizinho not in g or novo < g[vizinho]:
                g[vizinho] = novo
                pais[vizinho] = atual
                h = math.hypot(objetivo[0] - vizinho[0], objetivo[1] - vizinho[1])
                heapq.heappush(aberto, (novo + h, vizinho))
    return None


def replanejar(grade, inicio, objetivo, bloqueio):
    """Copia a grade, marca a celula bloqueada e busca um novo caminho."""
    # TODO: grade = grade.copy(); grade[bloqueio] = True; return buscar(...).
    raise NotImplementedError


def caminho_para_waypoints(caminho):
    return [(x, y, math.nan) for x, y in (centro(c) for c in caminho)]


def normaliza(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def controlador(robot, world, goal, cfg, dt, lidar_readings=None):
    if not ESTADO["replanejado"] and robot.x > 8.0:
        sim = ESTADO["sim"]
        sim.world.add_obstacle((BLOQUEIO[0], BLOQUEIO[1]), BLOQUEIO[2])
        caminho = replanejar(ESTADO["grade"], celula((robot.x, robot.y)), ESTADO["objetivo"], celula(BLOQUEIO))
        if caminho:
            sim.set_robot_waypoints(0, caminho_para_waypoints(caminho))
            ESTADO["replanejado"] = True
            print(f"replanejado={len(caminho)}")

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


def rodar(sim, limite=90.0):
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    grade = np.zeros((int(LARGURA / RESOLUCAO), int(ALTURA / RESOLUCAO)), dtype=bool)
    objetivo = celula(ALVO)

    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["obstacles"] = []
    config["robot"]["initial_pose"] = [INICIO[0], INICIO[1], 0.0]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador)
    ESTADO.update({"sim": sim, "grade": grade, "objetivo": objetivo})
    sim.set_robot_waypoints(0, [(INICIO[0], INICIO[1], math.nan), (ALVO[0], ALVO[1], math.nan)])

    print(f"Rota inicial: {INICIO} -> {ALVO}")
    rodar(sim)
    print(f"Posicao final: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulacao encerrada.")
