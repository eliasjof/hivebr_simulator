from __future__ import annotations
import numpy as np
import pygame
from .geometry import distance_between


class WaypointManager:
    def __init__(self, config: dict):
        self.waypoints = []
        self.current_index = 0
        self.goal_tolerance = float(config["waypoints"].get("goal_tolerance", 0.35))
        self.colors = config["colors"]
        self.show_tolerance_circle = bool(config["waypoints"].get("show_tolerance_circle", False))
        self.define_orientation = bool(config["waypoints"].get("define_orientation", False))

    def add_waypoint(self, pos):

        if len(pos) == 2:
            pos = (pos[0], pos[1], np.nan)        

        self.waypoints.append(
            np.array([pos[0], pos[1], pos[2]], dtype=float)
        )

    def clear(self):
        self.waypoints.clear()
        self.current_index = 0

    def has_waypoint(self):
        return self.current_index < len(self.waypoints)

    def get_current_waypoint(self):
        return self.waypoints[self.current_index] if self.has_waypoint() else None

    def update(self, robot_position):
        goal = self.get_current_waypoint()        

        if goal is None:
            return

        if distance_between(robot_position, goal[:2]) < self.goal_tolerance:
            self.current_index += 1

    def insert_waypoint_at_current(self, pos):
        if len(pos) == 2:
            pos = (pos[0], pos[1], np.nan)
        
        wp = np.array([pos[0], pos[1], pos[2]], dtype=float)
        
        # Insere na posição atual, empurrando o anterior para a frente
        self.waypoints.insert(self.current_index, wp)

    def status_text(self):
        return "None" if not self.has_waypoint() else f"{self.current_index + 1}/{len(self.waypoints)}"

    def draw(self, screen, camera):
        if not self.waypoints:
            return
        waypoint_color = tuple(self.colors["waypoint"])
        goal_color = tuple(self.colors["goal"])
        black = tuple(self.colors["black"])
        # for i in range(len(self.waypoints) - 1):
        #     pygame.draw.line(screen, waypoint_color, camera.world_to_screen(*self.waypoints[i]), camera.world_to_screen(*self.waypoints[i+1]), 2)
        for i, wp in enumerate(self.waypoints):
            color = goal_color if i == self.current_index else waypoint_color
            pygame.draw.circle(screen, color, camera.world_to_screen(*wp[:2]), 8)
            pygame.draw.circle(screen, black, camera.world_to_screen(*wp[:2]), 8, 2)


            # =========================
            # Círculo transparente
            # =========================
            if self.show_tolerance_circle:
                radius_px = max(5, int(self.goal_tolerance * camera.scale))

                circle_surface = pygame.Surface(
                    (radius_px * 2, radius_px * 2),
                    pygame.SRCALPHA
                )

                color2 = (*color, 120)

                pygame.draw.circle(
                    circle_surface,
                    color2,
                    (radius_px, radius_px),
                    radius_px
                )

                screen_pos = camera.world_to_screen(*wp[:2])

                screen.blit(
                    circle_surface,
                    (screen_pos[0] - radius_px,
                    screen_pos[1] - radius_px)
                )

            theta = wp[2]
            if not np.isnan(theta):

                px, py = camera.world_to_screen(wp[0], wp[1])

                arrow_len = max(20, int(0.5 * camera.scale))

                tip_x = px + arrow_len * np.cos(theta)
                tip_y = py - arrow_len * np.sin(theta)

                pygame.draw.line(
                    screen,
                    black,
                    (px, py),
                    (tip_x, tip_y),
                    3
                )

                head_size = 8

                pygame.draw.line(
                    screen,
                    black,
                    (tip_x, tip_y),
                    (
                        tip_x - head_size*np.cos(theta - np.pi/6),
                        tip_y + head_size*np.sin(theta - np.pi/6)
                    ),
                    3
                )

                pygame.draw.line(
                    screen,
                    black,
                    (tip_x, tip_y),
                    (
                        tip_x - head_size*np.cos(theta + np.pi/6),
                        tip_y + head_size*np.sin(theta + np.pi/6)
                    ),
                    3
                )
