"""Enxame centralizado: um único controlador comanda toda a frota.

Um SwarmController recebe o estado de todos os robôs e devolve {id: (v, omega)}.
Aqui ele mantém os quatro B-bots em um círculo em torno do centroide, ou em
uma linha se FORMACAO for "linha".
"""

import math

import numpy as np

from hivebr import SwarmController, SwarmExperiment
from hivebr.engine import load_config

FORMACAO = "circulo"  # "circulo" ou "linha"
RAIO = 1.5            # raio do círculo (m)
ESPACAMENTO = 1.0     # distância entre robôs na linha (m)
ROTACAO = 0.05        # rad/s com que o círculo gira
DT = 0.03             # tempo entre dois passos da simulação (s)


class Formacao(SwarmController):
    """Calcula um ponto-alvo para cada robô e manda os robôs até eles."""

    def __init__(self, tipo):
        self.tipo = tipo
        self.passos = 0
        self.ordem = None  # quem ocupa cada posição da formação; definido na 1a chamada

    def alvos(self, states, ids):
        """Ponto-alvo (x, y) de cada robô, em torno do centroide da frota."""
        cx = np.mean([states[i].x for i in ids])
        cy = np.mean([states[i].y for i in ids])
        n = len(ids)
        # Na primeira chamada, cada robô recebe a posição da formação na sua ordem
        # inicial (x na linha, ângulo no círculo): as trajetórias não se cruzam.
        if self.ordem is None:
            if self.tipo == "linha":
                chave = {i: states[i].x for i in ids}
            else:
                chave = {i: math.atan2(states[i].y - cy, states[i].x - cx) for i in ids}
            self.ordem = sorted(ids, key=lambda i: chave[i])
        alvos = {}
        for k, rid in enumerate(self.ordem):
            if self.tipo == "linha":
                alvos[rid] = (cx + (k - (n - 1) / 2) * ESPACAMENTO, cy)
            else:
                angulo = ROTACAO * self.passos * DT + 2 * math.pi * k / n
                alvos[rid] = (cx + RAIO * math.cos(angulo), cy + RAIO * math.sin(angulo))
        return alvos

    def loop(self, states):
        """Recebe {id: RobotState} e devolve {id: (v, omega)}."""
        self.passos += 1
        ids = sorted(states)
        alvos = self.alvos(states, ids)
        comandos = {}
        for rid in ids:
            st = states[rid]
            dx, dy = alvos[rid][0] - st.x, alvos[rid][1] - st.y
            desvio = math.atan2(dy, dx) - st.theta  # direção do alvo em relação ao robô
            erro = math.atan2(math.sin(desvio), math.cos(desvio))
            v = min(math.hypot(dx, dy), 0.4) * max(0.0, math.cos(erro))  # devagar se mal apontado
            comandos[rid] = (v, 2.0 * erro)
        return comandos


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config.setdefault("interaction", {})["collision_policy"] = "resolve"
    # Quatro robôs começando em fileira; a formação os reorganiza.
    frota = [{"id": i, "type": "differential", "initial_pose": [2.0 + 2.0 * i, 2.0, 0.0], "radius": 0.25}
             for i in range(4)]

    exp = SwarmExperiment(robots=frota, config=config)
    exp.set_controller(Formacao(FORMACAO))
    print(f"Formação em {FORMACAO}.")
    exp.run()
    print("Simulação encerrada.")
