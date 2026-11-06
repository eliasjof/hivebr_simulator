"""Início rápido: um B-bot diferencial percorrendo uma rota de waypoints.

O robô é controlado por um agente (HiveBrAgent). A cada passo da simulação o
engine chama loop(state, neighbors), que devolve (v, omega): velocidade linear
e velocidade angular.

Como usar: a simulação inicia sozinha; acompanhe o robô visitando os waypoints em ordem.
"""

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

# Rota do robô: pontos (x, y) em metros, visitados em ordem.
ROTA = [(6.0, 2.0), (14.0, 2.0), (14.0, 8.0), (6.0, 8.0)]


def normaliza_angulo(angulo):
    """Devolve o ângulo equivalente no intervalo [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class IrAoWaypoint(HiveBrAgent):
    """Controlador 'ir até o objetivo' que usa só a posição do waypoint."""

    def setup(self):
        # Valores vindos de assign_agent(...), ou padrões.
        self.kp = self.params.get("kp", 0.6)            # ganho da velocidade linear
        self.k_alpha = self.params.get("k_alpha", 1.5)  # ganho do giro
        self.vmax = 0.5                                 # limite de v (m/s)
        self.tolerancia = self.params.get("goal_tolerance", 0.1)

    def loop(self, state, neighbors):
        alvo = state.goal  # waypoint atual; None quando a rota terminou
        if alvo is None:
            return (0.0, 0.0)
        dx, dy = alvo[0] - state.x, alvo[1] - state.y
        distancia = float(np.hypot(dx, dy))
        if distancia < self.tolerancia:
            return (0.0, 0.0)
        # Como orientation é False, o ângulo final do waypoint é ignorado.
        erro = normaliza_angulo(np.arctan2(dy, dx) - state.theta)
        omega = self.k_alpha * erro
        # Só anda para frente quando está apontado para o alvo; de costas, só gira.
        v = min(self.kp * distancia, self.vmax) * max(0.0, np.cos(erro))
        return (v, omega)


if __name__ == "__main__":
    config = load_config("config/default.yaml")  # relativo ao diretório de trabalho
    frota = [{"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25}]

    # orientation=False: os waypoints são só posições (x, y).
    exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config, orientation=False)
    exp.assign_agent(robot_id=0, agent_class=IrAoWaypoint, kp=0.6)
    exp.assign_route(0, ROTA)

    print(f"Rota com {len(ROTA)} waypoints.")
    exp.run()  # bloqueia até a simulação parar
    print("Simulação encerrada.")
