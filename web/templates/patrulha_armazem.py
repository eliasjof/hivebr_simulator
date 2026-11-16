"""Atividade: patrulha de armazem com um B-bot.

O robo deve visitar as estacoes de ROTA na ordem definida. Complete o metodo
loop() do agente Patrulha: calcule a distancia e o angulo ate state.goal,
defina v proporcional a distancia e omega proporcional ao erro angular.

O console mostra o numero de estacoes; a simulacao termina quando voce parar.
"""

import math

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

ROTA = [(5.0, 9.0), (11.0, 9.0), (16.0, 5.0), (10.0, 2.0), (2.0, 2.0)]
PRATELEIRAS = [(8.0, 6.0, 0.6), (14.0, 9.0, 0.5), (13.0, 1.5, 0.5)]
VMAX = 0.7
KP_DIST = 1.2
KP_ANG = 2.5
TOLERANCIA = 0.15


def normaliza(angulo):
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class Patrulha(HiveBrAgent):
    """Agente que vai de estacao em estacao."""

    def setup(self):
        self.vmax = VMAX
        self.tolerancia = TOLERANCIA

    def loop(self, state, neighbors):
        alvo = state.goal
        if alvo is None:
            return (0.0, 0.0)

        dx = alvo[0] - state.x
        dy = alvo[1] - state.y
        distancia = float(np.hypot(dx, dy))
        if distancia < self.tolerancia:
            return (0.0, 0.0)

        # TODO: erro = normaliza(atan2(dy, dx) - state.theta)
        # v = min(vmax, KP_DIST * distancia) * max(0.0, cos(erro))
        # omega = KP_ANG * erro
        return (0.0, 0.0)


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in PRATELEIRAS]
    config.setdefault("interaction", {})["collision_policy"] = "resolve"

    frota = [{"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25}]
    exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config,
                          orientation=False, goal_tolerance=TOLERANCIA)
    exp.assign_agent(robot_id=0, agent_class=Patrulha)
    exp.assign_route(0, ROTA)

    print(f"Estacoes: {len(ROTA)}")
    exp.run()
    print("Patrulha encerrada.")
