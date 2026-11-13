"""Importando classes e funções de outro script do editor.

A aba ``agent_lib.py`` é enviada junto com este arquivo para a pasta de scripts
do Python, então o ``import`` abaixo funciona como em um projeto com vários
módulos: a classe e a função ficam no outro arquivo, não neste.
"""

from hivebr import SwarmExperiment
from hivebr.engine import load_config

# Importa a classe AgenteWaypoints e a função comprimento_rota do outro script.
from agent_lib import AgenteWaypoints, comprimento_rota

ROTA = [(5.0, 3.0), (12.0, 3.0), (12.0, 8.0), (5.0, 8.0)]


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    frota = [{"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25}]

    exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config, orientation=False)
    exp.assign_agent(robot_id=0, agent_class=AgenteWaypoints, kp=0.7)
    exp.assign_route(0, ROTA)

    print(f"Importado de agent_lib.py: {len(ROTA)} waypoints, {comprimento_rota(ROTA):.2f} m.")
    exp.run()
    print("Simulação encerrada.")
