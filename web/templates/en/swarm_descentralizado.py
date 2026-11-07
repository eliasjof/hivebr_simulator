"""Decentralized swarm: four B-bots, each with its own agent.

Each robot runs a HiveBrAgent that sees its own state and the neighbours within
comm_radius. Besides following its route, each robot keeps away from nearby
neighbours (separation). There is no central controller.
How to use: the simulation starts by itself. Keys 1 to 4 select a B-bot.
"""

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

# One route of (x, y) waypoints per robot, by id.
ROTAS = {
    0: [(2, 2), (5, 2), (5, 6), (2, 6)],
    1: [(5, 5), (10, 5), (10, 9), (5, 9)],
    2: [(18, 2), (15, 2), (15, 6), (18, 6)],
    3: [(18, 10), (14, 10), (14, 8), (18, 8)],
}


def normaliza_angulo(angulo):
    """Return the equivalent angle in the interval [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class AgenteDescentralizado(HiveBrAgent):
    """Go to the current waypoint and keep away from nearby neighbours."""

    def setup(self):
        self.kp = self.params.get("kp", 0.45)
        self.ganho_separacao = self.params.get("ganho_separacao", 0.9)
        self.tolerancia = self.params.get("goal_tolerance", 0.2)
        self.margem = 0.35  # extra clearance (m) between two robots

    def loop(self, state, neighbors):
        if state.goal is None:  # route finished
            return (0.0, 0.0)

        # 1. Attraction: go to the current waypoint (only the position matters).
        dx, dy = state.goal[0] - state.x, state.goal[1] - state.y
        distancia = float(np.hypot(dx, dy))
        if distancia < self.tolerancia:
            return (0.0, 0.0)
        erro = normaliza_angulo(np.arctan2(dy, dx) - state.theta)
        v = min(self.kp * distancia, 0.5) * max(0.0, np.cos(erro))
        omega = 1.5 * erro

        # 2. Separation: only visible neighbours (within comm_radius) count.
        for vizinho in neighbors.values():
            d = float(np.hypot(state.x - vizinho.x, state.y - vizinho.y))
            seguranca = state.radius + vizinho.radius + self.margem
            if 0.0 < d < seguranca:
                falta = seguranca - d
                direcao = normaliza_angulo(
                    np.arctan2(vizinho.y - state.y, vizinho.x - state.x) - state.theta
                )
                # Brake if the neighbour is ahead; steer to the opposite side.
                v -= self.ganho_separacao * falta * max(0.0, np.cos(direcao))
                omega -= 1.2 * falta * np.sin(direcao)
        return (v, omega)


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    # Collisions are resolved by pushing robots apart; neighbours visible up to 3 m.
    config["interaction"] = {
        "collision_policy": "resolve", "robot_collision": True, "robot_safety_margin": 0.0,
        "resolve_push": 0.05, "comm_radius": 3.0, "show_robot_links": True,
    }
    inicios = [(2, 2), (5, 5), (18, 2), (18, 10)]
    frota = [{"id": i, "type": "differential", "initial_pose": [x, y, 0.0], "radius": 0.25}
             for i, (x, y) in enumerate(inicios)]

    exp = SwarmExperiment(robots=frota, config=config, orientation=False)
    # Different gains: robot 0 is bolder; the others are more cautious.
    exp.assign_agent(robot_id=0, agent_class=AgenteDescentralizado, kp=0.45, ganho_separacao=0.5)
    exp.assign_agent(robot_ids=[1, 2, 3], agent_class=AgenteDescentralizado, ganho_separacao=0.9)
    for rid, rota in ROTAS.items():
        exp.assign_route(rid, rota)

    print(f"Swarm with {len(frota)} agents.")
    exp.run()
    print("Simulation finished.")
