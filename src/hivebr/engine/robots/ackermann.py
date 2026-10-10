from __future__ import annotations
import math
import numpy as np
import pygame
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


    def set_initial_pose(self,x,y,theta=0.0):
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

    def draw_path(self, screen, camera):
        if len(self.path) < 2:
            return
        pygame.draw.lines(screen, tuple(self.colors["path"]), False, [camera.world_to_screen(*p) for p in self.path], 2)

    def draw(self, screen, camera):
        # =========================
        # Corpo do robô
        # =========================
        corners = np.array([
            [ self.length/2,  self.width/2],
            [ self.length/2, -self.width/2],
            [-self.length/2, -self.width/2],
            [-self.length/2,  self.width/2]
        ])

        rot = np.array([
            [math.cos(self.theta), -math.sin(self.theta)],
            [math.sin(self.theta),  math.cos(self.theta)]
        ])

        pts = [
            camera.world_to_screen(*(rot @ c + self.position))
            for c in corners
        ]

        pygame.draw.polygon(screen, tuple(self.colors["robot"]), pts)

        # =========================
        # Círculo transparente
        # =========================
        radius_px = max(5, int(self.radius * camera.scale))

        circle_surface = pygame.Surface(
            (radius_px * 2, radius_px * 2),
            pygame.SRCALPHA
        )

        color = (*self.colors["robot"], 120)

        pygame.draw.circle(
            circle_surface,
            color,
            (radius_px, radius_px),
            radius_px
        )

        screen_pos = camera.world_to_screen(self.x, self.y)

        screen.blit(
            circle_surface,
            (screen_pos[0] - radius_px,
            screen_pos[1] - radius_px)
        )

        # =========================
        # Rodas
        # =========================

        wheel_length = self.length * 0.18
        wheel_width  = self.width * 0.12

        half_track = self.width / 2
        half_wb = self.wheel_base / 2

        # posições locais das rodas
        wheels = [
            (+half_wb, +half_track, self.theta + self.steer), # dianteira esquerda
            (+half_wb, -half_track, self.theta + self.steer), # dianteira direita
            (-half_wb, +half_track, self.theta),              # traseira esquerda
            (-half_wb, -half_track, self.theta),              # traseira direita
        ]

        for wx, wy, wtheta in wheels:

            # centro da roda no mundo
            wheel_center = rot @ np.array([wx, wy]) + self.position

            # rotação da roda
            wrot = np.array([
                [math.cos(wtheta), -math.sin(wtheta)],
                [math.sin(wtheta),  math.cos(wtheta)]
            ])

            # retângulo da roda
            wheel_corners = np.array([
                [ wheel_length/2,  wheel_width/2],
                [ wheel_length/2, -wheel_width/2],
                [-wheel_length/2, -wheel_width/2],
                [-wheel_length/2,  wheel_width/2]
            ])

            wheel_pts = [
                camera.world_to_screen(*(wrot @ c + wheel_center))
                for c in wheel_corners
            ]

            pygame.draw.polygon(
                screen,
                (139, 69, 19),
                wheel_pts
            )

        # =========================
        # Direção frontal
        # =========================
        front = self.position + np.array([
            math.cos(self.theta),
            math.sin(self.theta)
        ]) * (self.length / 2)

        pygame.draw.line(
            screen,
            tuple([192,192,186]),
            camera.world_to_screen(self.x, self.y),
            camera.world_to_screen(*front),
            3
        )
