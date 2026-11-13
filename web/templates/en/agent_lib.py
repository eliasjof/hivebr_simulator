"""Support library imported by the main script.

This is a separate tab in the editor. It defines a class and a function that
can be reused by any other script in the same project.
"""

import math

from hivebr import HiveBrAgent


def normaliza_angulo(angulo):
    """Return the equivalent angle in the interval [-pi, pi]."""
    return math.atan2(math.sin(angulo), math.cos(angulo))


def comprimento_rota(rota):
    """Add up the distances between consecutive waypoints on the route."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(rota, rota[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total


class AgenteWaypoints(HiveBrAgent):
    """'Go to goal' agent defined outside the main script."""

    def setup(self):
        self.kp = self.params.get("kp", 0.6)            # linear velocity gain
        self.k_alpha = self.params.get("k_alpha", 1.5)  # turning gain
        self.vmax = self.params.get("vmax", 0.5)        # limit for v (m/s)
        self.tolerancia = self.params.get("goal_tolerance", 0.1)

    def loop(self, state, neighbors):
        alvo = state.goal
        if alvo is None:
            return (0.0, 0.0)
        dx, dy = alvo[0] - state.x, alvo[1] - state.y
        distancia = math.hypot(dx, dy)
        if distancia < self.tolerancia:
            return (0.0, 0.0)
        erro = normaliza_angulo(math.atan2(dy, dx) - state.theta)
        omega = self.k_alpha * erro
        # Only moves forward when pointing at the target.
        v = min(self.kp * distancia, self.vmax) * max(0.0, math.cos(erro))
        return (v, omega)
