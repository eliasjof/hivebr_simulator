from __future__ import annotations
import math
import numpy as np
import pygame

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
    
    def set_initial_pose(self,x,y,theta=0.0):
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

    def draw_path(self, screen, camera):
        if len(self.path) < 2:
            return

        pygame.draw.lines(
            screen,
            tuple(self.colors["path"]),
            False,
            [camera.world_to_screen(*p) for p in self.path],
            2
        )

    def draw(self, screen, camera):
        center = np.array([self.x, self.y])

        color = tuple(self.colors["robot"])
        outline = tuple(self.colors["black"])

        # =====================================
        # Geometria do casco
        # =====================================

        W = 0.9 * self.radius
        L = math.sqrt(4*self.radius**2 - W**2)

        hull_local = np.array([
            [-0.50 * L, -0.50 * W],
            [ 0.25 * L, -0.50 * W],
            [ 0.50 * L,  0.00 * W],
            [ 0.25 * L,  0.50 * W],
            [-0.50 * L,  0.50 * W],
        ])

        bow_local = np.array([
            [ 0.50 * L, 0.0],
            [ 0.20 * L, -0.25 * W],
            [ 0.20 * L,  0.25 * W],
        ])

        # =====================================
        # Rotação
        # =====================================

        c = math.cos(self.theta)
        s = math.sin(self.theta)

        R = np.array([
            [c, -s],
            [s,  c]
        ])

        hull_world = (R @ hull_local.T).T + center
        bow_world = (R @ bow_local.T).T + center

        hull_screen = [
            camera.world_to_screen(*p)
            for p in hull_world
        ]

        bow_screen = [
            camera.world_to_screen(*p)
            for p in bow_world
        ]

        # =====================================
        # Desenho
        # =====================================

        pygame.draw.polygon(
            screen,
            color,
            hull_screen
        )

        pygame.draw.polygon(
            screen,
            color,
            bow_screen
        )

        pygame.draw.polygon(
            screen,
            outline,
            hull_screen,
            2
        )

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

        # linha central (opcional)

        front = center + np.array([
            math.cos(self.theta),
            math.sin(self.theta)
        ]) * L * 0.6

        pygame.draw.line(
            screen,
            tuple(self.colors["white"]),
            camera.world_to_screen(*center),
            camera.world_to_screen(*front),
            2
        )