from __future__ import annotations
import math
import numpy as np

from .differential import DifferentialRobot
from hivebr.engine.geometry import wrap_to_pi, clamp


class DifferentialRobotFirstOrder(DifferentialRobot):

    def __init__(self, config: dict):
        super().__init__(config)

        c = config["robot"]

        # constante de tempo do motor
        self.tau_v = float(c.get("tau_v", 0.5))

        # velocidade desejada
        self.v_ref = 0.0
        self.v = 0.0

        self.type = "differential_firstorder"

    def reset(self):
        super().reset()
        self.v_ref = 0.0
        self.v = 0.0

    def state(self):
        return {"type": "differential_firstorder", "x": self.x, "y": self.y, "theta": self.theta, "position": self.position.copy(), "v": self.v, "omega": self.omega, "v_ref": self.v_ref, "tau_v": self.tau_v}
        
    def set_initial_pose(self,x,y,theta=0.0):
        self.initial_pose = np.array([x, y, theta], dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()
        
    def step(self, command: dict, dt: float):

        # comandos vindos do controlador
        self.v_ref = clamp(
            float(command.get("v", 0.0)),
            -self.max_speed,
            self.max_speed
        )

        self.omega = clamp(
            float(command.get("omega", 0.0)),
            -self.max_omega,
            self.max_omega
        )

        # ------------------------------------
        # Dinâmica de primeira ordem:
        #
        # tau_v * dv/dt + v = v_ref
        # ------------------------------------
        dv = (self.v_ref - self.v) / self.tau_v

        self.v += dv * dt

        # proteção numérica
        self.v = clamp(
            self.v,
            -self.max_speed,
            self.max_speed
        )

        # cinemática
        self.x += self.v * math.cos(self.theta) * dt
        self.y += self.v * math.sin(self.theta) * dt

        self.theta = wrap_to_pi(
            self.theta + self.omega * dt
        )

        self.path.append(self.position.copy())

        if len(self.path) > self.path_max_length:
            self.path.pop(0)