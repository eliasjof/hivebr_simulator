"""Biblioteca de apoio importada pelo script principal.

Esta é uma aba separada no editor. Ela define uma classe e uma função que
podem ser reaproveitadas por qualquer outro script do mesmo projeto.
"""

import math

from hivebr import HiveBrAgent


def normaliza_angulo(angulo):
    """Devolve o ângulo equivalente no intervalo [-pi, pi]."""
    return math.atan2(math.sin(angulo), math.cos(angulo))


def comprimento_rota(rota):
    """Soma as distâncias entre os waypoints consecutivos da rota."""
    total = 0.0
    for (x1, y1), (x2, y2) in zip(rota, rota[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total


class AgenteWaypoints(HiveBrAgent):
    """Agente 'ir até o objetivo' definido fora do script principal."""

    def setup(self):
        self.kp = self.params.get("kp", 0.6)            # ganho da velocidade linear
        self.k_alpha = self.params.get("k_alpha", 1.5)  # ganho do giro
        self.vmax = self.params.get("vmax", 0.5)        # limite de v (m/s)
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
        # Só anda para frente quando está apontado para o alvo.
        v = min(self.kp * distancia, self.vmax) * max(0.0, math.cos(erro))
        return (v, omega)
