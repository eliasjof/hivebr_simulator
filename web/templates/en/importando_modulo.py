"""Importing classes and functions from another editor script.

The ``agent_lib.py`` tab is sent together with this file to the Python scripts
folder, so the ``import`` below works like in a project with several modules:
the class and the function live in the other file, not in this one.
"""

from hivebr import SwarmExperiment
from hivebr.engine import load_config

# Imports the AgenteWaypoints class and the comprimento_rota function from the other script.
from agent_lib import AgenteWaypoints, comprimento_rota

ROTA = [(5.0, 3.0), (12.0, 3.0), (12.0, 8.0), (5.0, 8.0)]


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    frota = [{"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25}]

    exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config, orientation=False)
    exp.assign_agent(robot_id=0, agent_class=AgenteWaypoints, kp=0.7)
    exp.assign_route(0, ROTA)

    print(f"Imported from agent_lib.py: {len(ROTA)} waypoints, {comprimento_rota(ROTA):.2f} m.")
    exp.run()
    print("Simulation finished.")
