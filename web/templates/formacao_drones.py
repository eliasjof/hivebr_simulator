"""Atividade: formacao de drones em um quadrado.

Quatro drones saem dos cantos da arena e devem formar um quadrado de 4 m de lado
centrado em (10, 6). Complete o metodo alvos(): ordene os ids e associe cada um
a um vertice de VERTICES.

O controlador ja converte o alvo em (v, omega); sem alvos() o experimento falha.
"""

import math

from hivebr import SwarmController, SwarmExperiment
from hivebr.engine import load_config

CENTRO = (10.0, 6.0)
LADO = 4.0
VERTICES = [
    (CENTRO[0] - LADO / 2.0, CENTRO[1] - LADO / 2.0),
    (CENTRO[0] - LADO / 2.0, CENTRO[1] + LADO / 2.0),
    (CENTRO[0] + LADO / 2.0, CENTRO[1] - LADO / 2.0),
    (CENTRO[0] + LADO / 2.0, CENTRO[1] + LADO / 2.0),
]
INICIOS = [(2.0, 2.0), (2.0, 10.0), (18.0, 2.0), (18.0, 10.0)]
TOLERANCIA = 0.15


class FormacaoQuadrada(SwarmController):
    """Distribui os robos nos vertices de um quadrado e vai ate eles."""

    def alvos(self, states):
        """Devolve {id: (x, y)} com um vertice por robo."""
        # TODO: ids = sorted(states); devolva {rid: VERTICES[k] ...}
        raise NotImplementedError

    def loop(self, states):
        alvos = self.alvos(states)
        comandos = {}
        for rid in sorted(states):
            st = states[rid]
            alvo = alvos[rid]
            dx, dy = alvo[0] - st.x, alvo[1] - st.y
            distancia = math.hypot(dx, dy)
            if distancia < TOLERANCIA:
                comandos[rid] = (0.0, 0.0)
                continue
            desvio = math.atan2(dy, dx) - st.theta
            erro = math.atan2(math.sin(desvio), math.cos(desvio))
            v = min(0.6, 1.2 * distancia) * max(0.0, math.cos(erro))
            comandos[rid] = (v, 2.5 * erro)
        return comandos


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["obstacles"] = []
    config.setdefault("interaction", {})["collision_policy"] = "resolve"

    frota = [
        {"id": i, "type": "differential", "initial_pose": [x, y, 0.0], "radius": 0.22}
        for i, (x, y) in enumerate(INICIOS)
    ]
    exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config,
                          orientation=False, goal_tolerance=TOLERANCIA)
    exp.set_controller(FormacaoQuadrada())

    print(f"Drones: {len(frota)}")
    exp.run()
    print("Formacao encerrada.")
