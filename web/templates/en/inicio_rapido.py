"""Quick start: a differential B-bot driving a route of waypoints.

The robot is controlled by an agent (HiveBrAgent). At every simulation step the
engine calls loop(state, neighbors), which returns (v, omega): linear velocity
and angular velocity.

How to use: the simulation starts by itself; watch the robot visit the waypoints in order.
"""

import numpy as np

from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config

# Robot route: (x, y) points in metres, visited in order.
ROTA = [(6.0, 2.0), (14.0, 2.0), (14.0, 8.0), (6.0, 8.0)]


def normaliza_angulo(angulo):
    """Return the equivalent angle in the interval [-pi, pi]."""
    return float(np.arctan2(np.sin(angulo), np.cos(angulo)))


class IrAoWaypoint(HiveBrAgent):
    """'Go to goal' controller that only uses the waypoint position."""

    def setup(self):
        # Values coming from assign_agent(...), or defaults.
        self.kp = self.params.get("kp", 0.6)            # linear velocity gain
        self.k_alpha = self.params.get("k_alpha", 1.5)  # turning gain
        self.vmax = 0.5                                 # limit for v (m/s)
        self.tolerancia = self.params.get("goal_tolerance", 0.1)

    def loop(self, state, neighbors):
        alvo = state.goal  # current waypoint; None when the route is over
        if alvo is None:
            return (0.0, 0.0)
        dx, dy = alvo[0] - state.x, alvo[1] - state.y
        distancia = float(np.hypot(dx, dy))
        if distancia < self.tolerancia:
            return (0.0, 0.0)
        # Since orientation is False, the waypoint final angle is ignored.
        erro = normaliza_angulo(np.arctan2(dy, dx) - state.theta)
        omega = self.k_alpha * erro
        # Only moves forward when pointing at the target; when facing away, it just turns.
        v = min(self.kp * distancia, self.vmax) * max(0.0, np.cos(erro))
        return (v, omega)


if __name__ == "__main__":
    config = load_config("config/default.yaml")  # relative to the working directory
    frota = [{"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25}]

    # orientation=False: waypoints are just (x, y) positions.
    exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config, orientation=False)
    exp.assign_agent(robot_id=0, agent_class=IrAoWaypoint, kp=0.6)
    exp.assign_route(0, ROTA)

    print(f"Route with {len(ROTA)} waypoints.")
    exp.run()  # blocks until the simulation stops
    print("Simulation finished.")
