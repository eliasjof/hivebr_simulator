from __future__ import annotations
import math
import numpy as np
import pygame
from .base import BaseRobot
from hivebr.engine.geometry import wrap_to_pi


class HolonomicRobot(BaseRobot):
    def __init__(self, config: dict):
        super().__init__(config)
        c = config["robot"]
        self.initial_pose = np.array(c.get("initial_pose", [2.0, 2.0, 0.0]), dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.radius = float(c.get("radius", 0.3))
        self.max_speed = float(c.get("max_speed", 2.0))
        self.path_max_length = int(c.get("path_max_length", 4000))
        self.vx = 0.0
        self.vy = 0.0
        self.colors = config["colors"]

    def set_initial_pose(self,x,y,theta=0.0):
        self.initial_pose = np.array([x, y, theta], dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()
        
    @property
    def position(self):
        return np.array([self.x, self.y], dtype=float)

    def reset(self):
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.vx = 0.0
        self.vy = 0.0
        self.path.clear()

    def state(self):
        return {"type": "holonomic", "x": self.x, "y": self.y, "theta": self.theta, "position": self.position.copy(), "vx": self.vx, "vy": self.vy}

    def step(self, command: dict, dt: float):
        vx = float(command.get("vx", 0.0))
        vy = float(command.get("vy", 0.0))
        norm = math.hypot(vx, vy)
        if norm > self.max_speed:
            scale = self.max_speed / norm
            vx *= scale
            vy *= scale
        self.vx, self.vy = vx, vy
        self.x += self.vx * dt
        self.y += self.vy * dt
        if norm > 1e-8:
            self.theta = wrap_to_pi(math.atan2(self.vy, self.vx))
        self.path.append(self.position.copy())
        if len(self.path) > self.path_max_length:
            self.path.pop(0)

    def draw_path(self, screen, camera):
        if len(self.path) < 2:
            return
        pygame.draw.lines(screen, tuple(self.colors["path"]), False, [camera.world_to_screen(*p) for p in self.path], 2)

    def draw(self, screen, camera):
        center = camera.world_to_screen(self.x, self.y)
        radius_px = max(5, int(self.radius * camera.scale))
        pygame.draw.circle(screen, tuple(self.colors["robot"]), center, radius_px)
        front = self.position + np.array([math.cos(self.theta), math.sin(self.theta)]) * self.radius * 1.6
        pygame.draw.line(screen, tuple(self.colors["white"]), center, camera.world_to_screen(*front), 3)

        # =========================
        # Rodas (4 omni wheels)
        # =========================
        wheel_len = self.radius * 0.6
        wheel_width = self.radius * 0.3
        
        rot = np.array([
            [math.cos(self.theta), -math.sin(self.theta)],
            [math.sin(self.theta),  math.cos(self.theta)]
        ])
        
        # Posições locais: 4 rodas nas extremidades
        offset = self.radius * 0.6
        wheels = [
            (offset, offset),    # Frente direita
            (offset, -offset),   # Frente esquerda
            (-offset, offset),   # Trás direita
            (-offset, -offset)   # Trás esquerda
        ]
        
        for wx, wy in wheels:
            # centro da roda no mundo
            wheel_center = rot @ np.array([wx, wy]) + self.position
            
            # retângulo da roda (orientada localmente)
            wheel_corners = np.array([
                [ wheel_len/2,  wheel_width/2],
                [ wheel_len/2, -wheel_width/2],
                [-wheel_len/2, -wheel_width/2],
                [-wheel_len/2,  wheel_width/2]
            ])
            
            # Rotacionar a roda
            wheel_pts = [
                camera.world_to_screen(*(rot @ c + wheel_center))
                for c in wheel_corners
            ]
            
            pygame.draw.polygon(
                screen,
                (139, 69, 19),
                wheel_pts
            )
