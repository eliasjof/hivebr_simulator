"""Demonstração: seis B-bots em duas patrulhas, com obstáculos, LiDAR e separação.

Dois grupos de três robôs patrulham, cada um, uma rota fechada. Cada robô é um
HiveBrAgent que vai até o próximo ponto (com orientação) e se afasta dos
vizinhos que estão perto. Os robôs se enxergam dentro de comm_radius e o LiDAR
detecta obstáculos e outros robôs.

O WaypointManager do engine não repete a rota: ao chegar ao último ponto ele
para. Por isso cada agente guarda a própria rota e volta ao início.

Como usar: a simulação inicia sozinha ao executar. Use Pausar para congelar e
Parar para encerrar; o resumo aparece no console ao parar.
"""

import math

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

# Duas rotas fechadas (x, y) em metros, uma para cada grupo.
ROTA_A = [(1.5, 6.0), (8.5, 6.0), (8.5, 10.5), (1.5, 10.5)]
ROTA_B = [(11.5, 1.5), (18.5, 1.5), (18.5, 5.5), (11.5, 5.5)]
# Obstáculos circulares (x, y, raio), afastados das duas rotas.
OBSTACULOS = [(10.0, 7.5, 0.8), (5.0, 3.0, 0.7), (15.0, 9.0, 0.8)]


def com_orientacao(pontos):
    """Acrescenta a cada ponto o ângulo do próximo trecho: (x, y, theta)."""
    rota = []
    for p, p_seguinte in zip(pontos, pontos[1:] + [pontos[0]]):
        theta = math.atan2(p_seguinte[1] - p[1], p_seguinte[0] - p[0])
        rota.append((p[0], p[1], theta))
    return rota


def normaliza_angulo(angulo):
    """Devolve o ângulo equivalente no intervalo [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class AgentePatrulha(HiveBrAgent):
    """Patrulha uma rota fechada em ciclo e se afasta dos vizinhos próximos."""

    def setup(self):
        self.rota = self.params["rota"]                       # lista de (x, y, theta)
        self.indice = self.params["inicio"] % len(self.rota)  # próximo ponto a visitar
        self.voltas = 0                                       # pontos atingidos
        self.tolerancia = 0.3                                 # m
        self.ganho_separacao = 0.9
        self.margem = 0.35                                    # folga extra entre robôs (m)

    def loop(self, state, neighbors):
        x_d, y_d, th_d = self.rota[self.indice]
        dx, dy = x_d - state.x, y_d - state.y
        if math.hypot(dx, dy) < self.tolerancia:
            # Chegou ao ponto: passa para o próximo; ao acabar a lista, recomeça.
            self.indice = (self.indice + 1) % len(self.rota)
            self.voltas += 1
            x_d, y_d, th_d = self.rota[self.indice]
            dx, dy = x_d - state.x, y_d - state.y

        # 1. Controle até o ponto (estilo Kanayama). Longe do ponto o robô só
        #    aponta para ele; a orientação do trecho seguinte entra perto dele.
        rho = math.hypot(dx, dy)
        alpha = normaliza_angulo(math.atan2(dy, dx) - state.theta)
        beta = normaliza_angulo(th_d - state.theta - alpha)
        v = min(0.35 * rho, 0.6) * max(0.0, math.cos(alpha))
        omega = 1.5 * alpha
        if rho < 0.8:
            omega -= 1.0 * beta

        # 2. Separação: vizinhos visíveis (dentro de comm_radius) muito perto.
        for vizinho in neighbors.values():
            d = math.hypot(state.x - vizinho.x, state.y - vizinho.y)
            seguranca = state.radius + vizinho.radius + self.margem
            if 0.0 < d < seguranca:
                falta = seguranca - d
                direcao = normaliza_angulo(
                    math.atan2(vizinho.y - state.y, vizinho.x - state.x) - state.theta
                )
                v -= self.ganho_separacao * falta * max(0.0, math.cos(direcao))
                omega -= 1.2 * falta * math.sin(direcao)
        return (v, omega)


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["lidar"] = {"enabled": True, "num_rays": 16, "range": 3.0, "fov_deg": 360}
    config["interaction"] = {
        "collision_policy": "resolve", "robot_collision": True, "robot_safety_margin": 0.0,
        "resolve_push": 0.05, "comm_radius": 3.0, "show_robot_links": True,
    }
    rota_a, rota_b = com_orientacao(ROTA_A), com_orientacao(ROTA_B)

    # (robô, rota do grupo, índice do ponto onde começa)
    inicios = [(0, rota_a, 0), (1, rota_a, 1), (2, rota_a, 2),
               (3, rota_b, 0), (4, rota_b, 1), (5, rota_b, 2)]
    frota = []
    for rid, rota, k in inicios:
        x, y, theta = rota[k]
        frota.append({"id": rid, "type": "differential", "initial_pose": [x, y, theta], "radius": 0.25})

    exp = SwarmExperiment(robots=frota, config=config, orientation=True)
    for rid, rota, k in inicios:
        # O agente começa visando o ponto seguinte ao da largada.
        exp.assign_agent(robot_id=rid, agent_class=AgentePatrulha, rota=rota, inicio=k + 1)

    print("Demonstração: 2 grupos de 3 B-bots.")
    exp.run()

    print("Resumo da patrulha:")
    for rid, agente in exp.agents.items():
        print(f"  B-bot {rid}: {agente.voltas} pontos atingidos")
    exp.print_collisions()
