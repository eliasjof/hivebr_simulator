"""Centralized swarm: a single controller drives the whole fleet.

A SwarmController receives the state of every robot and returns {id: (v, omega)}.
Here it keeps the four B-bots in a circle around the centroid, or in a
line if FORMACAO is "linha".
"""

import math

import numpy as np

from hivebr import SwarmController, SwarmExperiment
from hivebr.engine import load_config

FORMACAO = "circulo"  # "circulo" (circle) or "linha" (line)
RAIO = 1.5            # circle radius (m)
ESPACAMENTO = 1.0     # distance between robots in the line (m)
ROTACAO = 0.05        # rad/s at which the circle rotates
DT = 0.03             # time between two simulation steps (s)


class Formacao(SwarmController):
    """Compute a target point for each robot and send the robots to them."""

    def __init__(self, tipo):
        self.tipo = tipo
        self.passos = 0
        self.ordem = None  # who takes each formation slot; set on the first call

    def alvos(self, states, ids):
        """Target (x, y) of each robot, around the fleet centroid."""
        cx = np.mean([states[i].x for i in ids])
        cy = np.mean([states[i].y for i in ids])
        n = len(ids)
        # On the first call, each robot gets the formation slot matching its initial
        # order (x in the line, angle in the circle): trajectories do not cross.
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
        """Receive {id: RobotState} and return {id: (v, omega)}."""
        self.passos += 1
        ids = sorted(states)
        alvos = self.alvos(states, ids)
        comandos = {}
        for rid in ids:
            st = states[rid]
            dx, dy = alvos[rid][0] - st.x, alvos[rid][1] - st.y
            desvio = math.atan2(dy, dx) - st.theta  # target direction relative to the robot
            erro = math.atan2(math.sin(desvio), math.cos(desvio))
            v = min(math.hypot(dx, dy), 0.4) * max(0.0, math.cos(erro))  # slow when badly aimed
            comandos[rid] = (v, 2.0 * erro)
        return comandos


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config.setdefault("interaction", {})["collision_policy"] = "resolve"
    # Four robots starting in a row; the formation rearranges them.
    frota = [{"id": i, "type": "differential", "initial_pose": [2.0 + 2.0 * i, 2.0, 0.0], "radius": 0.25}
             for i in range(4)]

    exp = SwarmExperiment(robots=frota, config=config)
    exp.set_controller(Formacao(FORMACAO))
    print(f"Formation: {FORMACAO}.")
    exp.run()
    print("Simulation finished.")
