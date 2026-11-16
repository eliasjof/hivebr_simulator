"""Activity: warehouse inventory with a decentralized swarm.

Four B-bots check the shelves in parallel. Each robot receives a route of
inventory stations and must visit them in order. Complete the loop() method of
the Inventariante agent: go to state.goal with v proportional to the distance
and omega proportional to the angular error.

The console shows the total number of stations. The simulation ends when you
stop it.
"""

import math

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

ROTAS = {
    0: [(4.0, 2.0), (4.0, 6.0), (2.0, 8.0)],
    1: [(7.0, 6.0), (7.0, 9.0), (4.0, 9.0)],
    2: [(12.0, 6.0), (12.0, 9.0), (15.0, 9.0)],
    3: [(17.0, 6.0), (14.0, 6.0), (14.0, 2.0)],
}
INICIOS = [(2.0, 2.0), (7.0, 2.0), (12.0, 2.0), (17.0, 2.0)]
PRATELEIRAS = [
    (5.5, 4.0, 0.5),
    (5.5, 8.0, 0.5),
    (9.5, 4.0, 0.5),
    (9.5, 8.0, 0.5),
    (16.0, 4.0, 0.5),
    (16.0, 8.0, 0.5),
]
VMAX = 0.7
KP_DIST = 1.2
KP_ANG = 2.5
TOLERANCIA = 0.15


def normaliza(angulo):
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class Inventariante(HiveBrAgent):
    """Agent that drives through the inventory stations of its aisle."""

    def setup(self):
        self.vmax = VMAX
        self.tolerancia = self.params.get("goal_tolerance", TOLERANCIA)

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

    frota = [
        {"id": i, "type": "differential", "initial_pose": [x, y, 0.0], "radius": 0.22}
        for i, (x, y) in enumerate(INICIOS)
    ]
    exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config,
                          orientation=False, goal_tolerance=TOLERANCIA)
    exp.assign_agent(robot_ids=[0, 1, 2, 3], agent_class=Inventariante)
    for rid, rota in ROTAS.items():
        exp.assign_route(rid, rota)

    total = sum(len(rota) for rota in ROTAS.values())
    print(f"Stations: {total}")
    exp.run()
    print("Inventory finished.")
