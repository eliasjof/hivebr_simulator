from __future__ import annotations
import math
import numpy as np
from .base import BaseRobot
from hivebr.engine.geometry import wrap_to_pi, clamp


class AckermannRobot(BaseRobot):
    def __init__(self, config: dict):
        super().__init__(config)
        c = config["robot"]
        self.initial_pose = np.array(c.get("initial_pose", [2.0, 2.0, 0.0]), dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.wheel_base = float(c.get("wheel_base", 0.5))
        self.length = float(c.get("length", 0.8))
        self.width = float(c.get("width", 0.4))
        self.radius = float(c.get("radius", 0.4))
        self.max_speed = float(c.get("max_speed", 3.0))
        self.max_steer = float(c.get("max_steer", 0.6))
        self.path_max_length = int(c.get("path_max_length", 4000))
        self.speed = 0.0
        self.steer = 0.0
        self.colors = config["colors"]

    def set_initial_pose(self, x, y, theta=0.0):
        self.initial_pose = np.array([x, y, theta], dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()

    @property
    def position(self):
        return np.array([self.x, self.y], dtype=float)

    def reset(self):
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.speed = 0.0
        self.steer = 0.0
        self.path.clear()

    def state(self):
        return {"type": "ackermann", "x": self.x, "y": self.y, "theta": self.theta, "position": self.position.copy(), "speed": self.speed, "steer": self.steer}

    def step(self, command: dict, dt: float):
        self.speed = clamp(float(command.get("speed", 0.0)), -self.max_speed, self.max_speed)
        self.steer = clamp(float(command.get("steer", 0.0)), -self.max_steer, self.max_steer)
        self.x += self.speed * math.cos(self.theta) * dt
        self.y += self.speed * math.sin(self.theta) * dt
        self.theta += (self.speed / self.wheel_base) * math.tan(self.steer) * dt
        self.theta = wrap_to_pi(self.theta)
        self.path.append(self.position.copy())
        if len(self.path) > self.path_max_length:
            self.path.pop(0)

    def clear_path(self):
        self.path.clear()

    # draw_path and draw methods removed - rendering is handled by frontend