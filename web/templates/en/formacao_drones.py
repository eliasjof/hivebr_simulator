"""Activity: drone formation in a square.

Four drones leave the corners of the arena and must form a 4 m square centred at
(10, 6). Complete the alvos() method: sort the ids and assign each one to a
vertex of VERTICES.

The controller already converts the target into (v, omega); without alvos() the
experiment fails.
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
    """Assign the robots to the corners of a square and drive them there."""

    def alvos(self, states):
        """Return {id: (x, y)} with one vertex per robot."""
        # TODO: ids = sorted(states); return {rid: VERTICES[k] ...}
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
    print("Formation finished.")
