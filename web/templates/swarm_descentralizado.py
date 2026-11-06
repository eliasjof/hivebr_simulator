"""Enxame descentralizado: quatro B-bots, cada um com seu próprio agente.

Cada robô roda um HiveBrAgent que enxerga o próprio estado e os vizinhos dentro
de comm_radius. Além de seguir a rota, cada robô se afasta dos vizinhos que
estão perto (separação). Não há controlador central.
Como usar: a simulação inicia sozinha. As teclas 1 a 4 selecionam um B-bot.
"""

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

# Uma rota de waypoints (x, y) por robô, pelo id.
ROTAS = {
    0: [(2, 2), (5, 2), (5, 6), (2, 6)],
    1: [(5, 5), (10, 5), (10, 9), (5, 9)],
    2: [(18, 2), (15, 2), (15, 6), (18, 6)],
    3: [(18, 10), (14, 10), (14, 8), (18, 8)],
}


def normaliza_angulo(angulo):
    """Devolve o ângulo equivalente no intervalo [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class AgenteDescentralizado(HiveBrAgent):
    """Vai até o waypoint atual e se afasta dos vizinhos próximos."""

    def setup(self):
        self.kp = self.params.get("kp", 0.45)
        self.ganho_separacao = self.params.get("ganho_separacao", 0.9)
        self.tolerancia = self.params.get("goal_tolerance", 0.2)
        self.margem = 0.35  # folga extra (m) entre dois robôs

    def loop(self, state, neighbors):
        if state.goal is None:  # rota terminada
            return (0.0, 0.0)

        # 1. Atração: ir até o waypoint atual (só a posição importa).
        dx, dy = state.goal[0] - state.x, state.goal[1] - state.y
        distancia = float(np.hypot(dx, dy))
        if distancia < self.tolerancia:
            return (0.0, 0.0)
        erro = normaliza_angulo(np.arctan2(dy, dx) - state.theta)
        v = min(self.kp * distancia, 0.5) * max(0.0, np.cos(erro))
        omega = 1.5 * erro

        # 2. Separação: só vizinhos visíveis (dentro de comm_radius) contam.
        for vizinho in neighbors.values():
            d = float(np.hypot(state.x - vizinho.x, state.y - vizinho.y))
            seguranca = state.radius + vizinho.radius + self.margem
            if 0.0 < d < seguranca:
                falta = seguranca - d
                direcao = normaliza_angulo(
                    np.arctan2(vizinho.y - state.y, vizinho.x - state.x) - state.theta
                )
                # Freia se o vizinho estiver à frente; desvia para o lado oposto.
                v -= self.ganho_separacao * falta * max(0.0, np.cos(direcao))
                omega -= 1.2 * falta * np.sin(direcao)
        return (v, omega)


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    # Colisões se resolvem empurrando os robôs; vizinhos visíveis até 3 m.
    config["interaction"] = {
        "collision_policy": "resolve", "robot_collision": True, "robot_safety_margin": 0.0,
        "resolve_push": 0.05, "comm_radius": 3.0, "show_robot_links": True,
    }
    inicios = [(2, 2), (5, 5), (18, 2), (18, 10)]
    frota = [{"id": i, "type": "differential", "initial_pose": [x, y, 0.0], "radius": 0.25}
             for i, (x, y) in enumerate(inicios)]

    exp = SwarmExperiment(robots=frota, config=config, orientation=False)
    # Ganhos diferentes: o robô 0 é mais ousado; os outros, mais cautelosos.
    exp.assign_agent(robot_id=0, agent_class=AgenteDescentralizado, kp=0.45, ganho_separacao=0.5)
    exp.assign_agent(robot_ids=[1, 2, 3], agent_class=AgenteDescentralizado, ganho_separacao=0.9)
    for rid, rota in ROTAS.items():
        exp.assign_route(rid, rota)

    print(f"Enxame com {len(frota)} agentes.")
    exp.run()
    print("Simulação encerrada.")
