from __future__ import annotations
import math
import numpy as np
from .base import BaseRobot
from hivebr.engine.geometry import wrap_to_pi, clamp


class BoatRobot(BaseRobot):

    def __init__(self, config: dict):
        super().__init__(config)

        c = config["robot"]

        self.initial_pose = np.array(
            c.get("initial_pose", [2.0, 2.0, 0.0]),
            dtype=float
        )

        self.x, self.y, self.theta = self.initial_pose.tolist()

        self.radius = float(c.get("radius", 0.35))

        self.max_speed = float(c.get("max_speed", 2.0))
        self.max_omega = float(c.get("max_omega", 1.0))

        self.path_max_length = int(
            c.get("path_max_length", 4000)
        )

        self.v = 0.0
        self.omega = 0.0

        self.colors = config["colors"]

    def set_initial_pose(self, x, y, theta=0.0):
        self.initial_pose = np.array([x, y, theta], dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()

    @property
    def position(self):
        return np.array([self.x, self.y], dtype=float)

    def reset(self):
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.v = 0.0
        self.omega = 0.0
        self.path.clear()

    def state(self):
        return {
            "type": "boat",
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "position": self.position.copy(),
            "v": self.v,
            "omega": self.omega
        }

    def step(self, command: dict, dt: float):
        self.v = clamp(
            float(command.get("v", 0.0)),
            -self.max_speed,
            self.max_speed
        )

        self.omega = clamp(
            float(command.get("omega", 0.0)),
            -self.max_omega,
            self.max_omega
        )

        self.x += self.v * math.cos(self.theta) * dt
        self.y += self.v * math.sin(self.theta) * dt

        self.theta = wrap_to_pi(
            self.theta + self.omega * dt
        )

        self.path.append(self.position.copy())

        if len(self.path) > self.path_max_length:
            self.path.pop(0)

    def clear_path(self):
        self.path.clear()

    # draw_path and draw methods removed - rendering is handled by frontend