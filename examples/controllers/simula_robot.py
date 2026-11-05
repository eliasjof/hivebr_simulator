import numpy as np
import math
from hivebr.engine.robots.differential import DifferentialRobot

class SimulateRobot(DifferentialRobot):
    """
    Versão leve do robô para otimizações (sem GUI, sem Pygame).
    """
    def __init__(self, config):
        super().__init__(config)
        self.history = []

    def step(self, command, dt):
        # Sobrescreve o step para não depender de pygame ou lógica visual pesada
        self.v = max(min(float(command.get("v", 0.0)), self.max_speed), -self.max_speed)
        self.omega = max(min(float(command.get("omega", 0.0)), self.max_omega), -self.max_omega)
        
        # Atualização física básica
        self.x += self.v * math.cos(self.theta) * dt
        self.y += self.v * math.sin(self.theta) * dt
        self.theta = (self.theta + self.omega * dt + math.pi) % (2 * math.pi) - math.pi
        
        # Salva estado para avaliação da otimização
        self.history.append((self.x, self.y, self.theta))

    def reset(self):
        super().reset()
        self.history = []

def potential_field_controller(robot, goal, obstacles):
    """
    Exemplo rápido de controlador de campo potencial.
    """
    # Exemplo simples de atração ao alvo e repulsão aos obstáculos
    k_att = 1.0
    k_rep = 5.0
    
    # Vetor atração
    att = k_att * (np.array(goal[:2]) - np.array([robot.x, robot.y]))
    
    # Vetor repulsão (simples)
    rep = np.array([0.0, 0.0])
    for obs in obstacles:
        obs_pos = np.array(obs[:2])
        dist = np.linalg.norm(np.array([robot.x, robot.y]) - obs_pos)
        if dist < 2.0: # Raio de influência
            rep += k_rep * (1.0/dist - 1.0/2.0) * (np.array([robot.x, robot.y]) - obs_pos) / dist**3
            
    force = att + rep
    
    # Conversão para v, w (simplificado)
    v = np.linalg.norm(force)
    w = math.atan2(force[1], force[0]) - robot.theta
    w = (w + math.pi) % (2 * math.pi) - math.pi
    
    return {"v": v, "omega": w}

import matplotlib.pyplot as plt


if __name__ == "__main__":
    # Exemplo de uso rápido para rodar 1000 simulações
    config = {"robot": {"max_speed": 2.0, "max_omega": 2.0}, "colors": {"robot": [0,0,0], "path": [0,0,0]}}
    robot = SimulateRobot(config)
    goal = [10.0, 10.0]
    obstacles = [[5.0, 5.0, 0.5], [9.0, 8.0, 0.5]]
    
    for _ in range(200):
        cmd = potential_field_controller(robot, goal, obstacles)
        robot.step(cmd, 0.1)
        
    print(f"Simulação finalizada. Histórico: {len(robot.history)} passos.")

    # Plot dos resultados
    history = np.array(robot.history)
    plt.figure(figsize=(8, 8))
    plt.plot(history[:, 0], history[:, 1], label="Caminho do Robô")
    plt.scatter(goal[0], goal[1], color="green", label="Alvo")
    for obs in obstacles:
        circle = plt.Circle((obs[0], obs[1]), obs[2], color="red", label="Obstáculo")
        plt.gca().add_patch(circle)
    
    plt.title("Simulação Rápida - Caminho do Robô")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.grid(True)
    plt.axis("equal")
    plt.show()
