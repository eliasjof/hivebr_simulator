"""Demo: six B-bots in two patrols, with obstacles, LiDAR and separation.

Two groups of three robots each patrol a closed route. Each robot is a
HiveBrAgent that goes to the next point (with orientation) and keeps away from
nearby neighbours. Robots see each other within comm_radius and the LiDAR
detects obstacles and other robots.

The engine's WaypointManager does not repeat the route: on reaching the last
point it stops. That is why each agent keeps its own route and wraps around.

How to use: the simulation starts by itself when you run it. Use Pause to freeze
and Stop to end; the summary appears in the console when it stops.
"""

import math

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

# Two closed (x, y) routes in metres, one for each group.
ROTA_A = [(1.5, 6.0), (8.5, 6.0), (8.5, 10.5), (1.5, 10.5)]
ROTA_B = [(11.5, 1.5), (18.5, 1.5), (18.5, 5.5), (11.5, 5.5)]
# Circular obstacles (x, y, radius), away from both routes.
OBSTACULOS = [(10.0, 7.5, 0.8), (5.0, 3.0, 0.7), (15.0, 9.0, 0.8)]


def com_orientacao(pontos):
    """Add to each point the angle of the next leg: (x, y, theta)."""
    rota = []
    for p, p_seguinte in zip(pontos, pontos[1:] + [pontos[0]]):
        theta = math.atan2(p_seguinte[1] - p[1], p_seguinte[0] - p[0])
        rota.append((p[0], p[1], theta))
    return rota


def normaliza_angulo(angulo):
    """Return the equivalent angle in the interval [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class AgentePatrulha(HiveBrAgent):
    """Patrol a closed route in a cycle and keep away from nearby neighbours."""

    def setup(self):
        self.rota = self.params["rota"]                       # list of (x, y, theta)
        self.indice = self.params["inicio"] % len(self.rota)  # next point to visit
        self.voltas = 0                                       # points reached
        self.tolerancia = 0.3                                 # m
        self.ganho_separacao = 0.9
        self.margem = 0.35                                    # extra clearance between robots (m)

    def loop(self, state, neighbors):
        x_d, y_d, th_d = self.rota[self.indice]
        dx, dy = x_d - state.x, y_d - state.y
        if math.hypot(dx, dy) < self.tolerancia:
            # Reached the point: move on to the next; at the end of the list, start over.
            self.indice = (self.indice + 1) % len(self.rota)
            self.voltas += 1
            x_d, y_d, th_d = self.rota[self.indice]
            dx, dy = x_d - state.x, y_d - state.y

        # 1. Control towards the point (Kanayama style). Far from the point the robot
        #    just aims at it; the orientation of the next leg kicks in near it.
        rho = math.hypot(dx, dy)
        alpha = normaliza_angulo(math.atan2(dy, dx) - state.theta)
        beta = normaliza_angulo(th_d - state.theta - alpha)
        v = min(0.35 * rho, 0.6) * max(0.0, math.cos(alpha))
        omega = 1.5 * alpha
        if rho < 0.8:
            omega -= 1.0 * beta

        # 2. Separation: visible neighbours (within comm_radius) that are too close.
        for vizinho in neighbors.values():
            d = math.hypot(state.x - vizinho.x, state.y - vizinho.y)
            seguranca = state.radius + vizinho.radius + self.margem
            if 0.0 < d < seguranca:
                falta = seguranca - d
                direcao = normaliza_angulo(
                    math.atan2(vizinho.y - state.y, vizinho.x - state.x) - state.theta
                )
                v -= self.ganho_separacao * falta * max(0.0, math.cos(direcao))
                omega -= 1.2 * falta * math.sin(direcao)
        return (v, omega)


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["obstacles"] = [{"x": x, "y": y, "radius": r} for x, y, r in OBSTACULOS]
    config["lidar"] = {"enabled": True, "num_rays": 16, "range": 3.0, "fov_deg": 360}
    config["interaction"] = {
        "collision_policy": "resolve", "robot_collision": True, "robot_safety_margin": 0.0,
        "resolve_push": 0.05, "comm_radius": 3.0, "show_robot_links": True,
    }
    rota_a, rota_b = com_orientacao(ROTA_A), com_orientacao(ROTA_B)

    # (robot, group route, index of the point where it starts)
    inicios = [(0, rota_a, 0), (1, rota_a, 1), (2, rota_a, 2),
               (3, rota_b, 0), (4, rota_b, 1), (5, rota_b, 2)]
    frota = []
    for rid, rota, k in inicios:
        x, y, theta = rota[k]
        frota.append({"id": rid, "type": "differential", "initial_pose": [x, y, theta], "radius": 0.25})

    exp = SwarmExperiment(robots=frota, config=config, orientation=True)
    for rid, rota, k in inicios:
        # The agent starts aiming at the point after the starting one.
        exp.assign_agent(robot_id=rid, agent_class=AgentePatrulha, rota=rota, inicio=k + 1)

    print("Demo: 2 groups of 3 B-bots.")
    exp.run()

    print("Patrol summary:")
    for rid, agente in exp.agents.items():
        print(f"  B-bot {rid}: {agente.voltas} points reached")
    exp.print_collisions()
