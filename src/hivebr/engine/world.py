from __future__ import annotations

import math
import numpy as np
import pygame

from pathlib import Path


assets_dir = Path(__file__).parent / "assets"
class World:
    def __init__(self, config: dict):
        self.config = config
        self.width = float(config["world"]["width"])
        self.height = float(config["world"]["height"])

        self.grid_size = float(
            config["world"].get("grid_size", 1.0)
        )

        # Raio padrão usado para novos obstáculos adicionados por mouse
        self.default_obstacle_radius = float(
            config["world"].get("default_obstacle_radius", 0.4)
        )

        self.show_origin = bool(
            config["world"].get("show_origin", True)
        )

        self.show_axes = bool(
            config["world"].get("show_axes", True)
        )

        # self.colors = config["colors"] # Removido, vamos usar a property
        
        self.obstacles = []

        for obs in config["world"].get("obstacles", []):
            self.obstacles.append(
                self._parse_obstacle(obs)
            )

        self.recharge_image = pygame.image.load(assets_dir /"recharge_place.png").convert_alpha()

        self.recharge_places = []

        for rp in config["world"].get("recharge_places", []):
            self.recharge_places.append(
                self._parse_obstacle(rp)
            )
        
        self.robot_radius = float(config["robot"].get("radius", 0.4))

        self.grid_map = None
        if "map_image" in config["world"]:
            from .occupancy_grid import OccupancyGridMap
            self.grid_map = OccupancyGridMap(
                image_path=config["world"]["map_image"],
                resolution=float(config["world"]["resolution"]),
                robot_radius=self.robot_radius,
                colors=self.colors
            )
            self.width = self.grid_map.width_m
            self.height = self.grid_map.height_m

        self.show_inflation = bool(
            config["world"].get("show_inflation", True)
        )

    @property
    def colors(self):
        return self.config["colors"]

    def load_map(self, image_path: str, resolution: float):
        """
        Loads a map dynamically, bypassing YAML configuration.
        """
        from .occupancy_grid import OccupancyGridMap
        self.grid_map = OccupancyGridMap(
            image_path=image_path,
            resolution=float(resolution),
            robot_radius=self.robot_radius,
            colors=self.colors
        )
        self.width = self.grid_map.width_m
        self.height = self.grid_map.height_m

    def set_grid_map(self, grid_map):
        self.grid_map = grid_map
        self.width = self.grid_map.width_m
        self.height = self.grid_map.height_m

    def _parse_obstacle(self, obs):
        """
        Converte obstáculo para o formato padrão interno:

            np.array([cx, cy, radius])

        Aceita também formato antigo [cx, cy],
        usando default_obstacle_radius.
        """

        if len(obs) == 2:
            cx, cy = obs
            radius = self.default_obstacle_radius

        elif len(obs) == 3:
            cx, cy, radius = obs

        else:
            raise ValueError(
                "Obstáculo deve estar no formato [cx, cy] "
                "ou [cx, cy, radius]."
            )

        return np.array(
            [float(cx), float(cy), float(radius)],
            dtype=float
        )

    def add_obstacle(self, pos, radius=None):
        """
        Adiciona obstáculo no mundo.

        Parameters
        ----------
        pos:
            posição [x, y]
        radius:
            raio do obstáculo. Se None, usa default_obstacle_radius.
        """

        if radius is None:
            radius = self.default_obstacle_radius

        self.obstacles.append(
            np.array(
                [float(pos[0]), float(pos[1]), float(radius)],
                dtype=float
            )
        )

    def clear_obstacles(self):
        self.obstacles.clear()

    def get_position(self, obs):
        return obs[:2]

    def obstacle_radius(self, obs):
        return float(obs[2])
    
    
    def clear_obstacles(self):
        self.obstacles.clear()

    
    def add_obstacle(self, pos, radius=None):
        if radius is None:
            radius = self.default_obstacle_radius

        self.obstacles.append(
            np.array(
                [float(pos[0]), float(pos[1]), float(radius)],
                dtype=float
            )
        )
        


    def distance_to_nearest_obstacle(self, position):
        if not self.obstacles:
            return float("inf")

        distances = []

        for obs in self.obstacles:
            center = self.get_position(obs)
            radius = self.obstacle_radius(obs)

            distance = np.linalg.norm(position - center) - radius
            distances.append(distance)

        return float(min(distances))

    def draw_grid(self, screen, camera):
        step_px = self.grid_size * camera.scale

        if step_px < 8:
            return

        bottom_left = camera.screen_to_world(
            0,
            camera.viewport_height
        )

        top_right = camera.screen_to_world(
            camera.viewport_width,
            0
        )

        min_x, min_y = bottom_left
        max_x, max_y = top_right

        start_x = math.floor(min_x / self.grid_size) * self.grid_size
        end_x = math.ceil(max_x / self.grid_size) * self.grid_size

        start_y = math.floor(min_y / self.grid_size) * self.grid_size
        end_y = math.ceil(max_y / self.grid_size) * self.grid_size

        color = tuple(self.colors["grid"])

        x = start_x
        while x <= end_x:
            pygame.draw.line(
                screen,
                color,
                camera.world_to_screen(x, min_y),
                camera.world_to_screen(x, max_y)
            )

            x += self.grid_size

        y = start_y
        while y <= end_y:
            pygame.draw.line(
                screen,
                color,
                camera.world_to_screen(min_x, y),
                camera.world_to_screen(max_x, y)
            )

            y += self.grid_size

    def draw_origin(self, screen, camera):
        if not self.show_origin:
            return

        origin = camera.world_to_screen(0.0, 0.0)

        red = tuple(self.colors["red"])
        # white = tuple(self.colors["black"])

        # pygame.draw.circle(
        #     screen,
        #     white,
        #     origin,
        #     3
        # )

        pygame.draw.line(
            screen,
            red,
            (origin[0] - 10, origin[1]),
            (origin[0] + 10, origin[1]),
            2
        )

        pygame.draw.line(
            screen,
            red,
            (origin[0], origin[1] - 10),
            (origin[0], origin[1] + 10),
            2
        )

        

    def draw_axes(self, screen, camera):
        if not self.show_axes:
            return

        red = tuple(self.colors["red"])
        green = tuple(self.colors["green"])

        origin = camera.world_to_screen(0.0, 0.0)
        x_tip = camera.world_to_screen(camera.margin_x, 0.0)
        y_tip = camera.world_to_screen(0.0, camera.margin_y)

        pygame.draw.line(
            screen,
            red,
            origin,
            x_tip,
            2
        )

        pygame.draw.line(
            screen,
            green,
            origin,
            y_tip,
            2
        )

    def draw_recharge_places(self, screen, camera):
        # Obter tamanho original da imagem para manter proporção
        orig_w, orig_h = self.recharge_image.get_size()
        aspect_ratio = orig_h / orig_w
        
        for rp in self.recharge_places:
            center = self.get_position(rp)
            screen_pos = camera.world_to_screen(center[0], center[1])
            
            # Escala baseada no zoom da câmera. 
            # Define uma largura base de 32 pixels
            base_width = 16
            scaled_width = int(base_width * camera.zoom)
            scaled_height = int(scaled_width * aspect_ratio)
            
            img = pygame.transform.smoothscale(self.recharge_image, (scaled_width, scaled_height))
            rect = img.get_rect(center=screen_pos)
            screen.blit(img, rect)

    def get_recharge_place(self, id):
        if 0 <= id < len(self.recharge_places):
            return self.get_position(self.recharge_places[id])
        return None

    def draw_obstacles(self, screen, camera):
        color = tuple(self.colors["obstacle"])

        for obs in self.obstacles:
            center = self.get_position(obs)
            radius = self.obstacle_radius(obs)

            pygame.draw.circle(
                screen,
                color,
                camera.world_to_screen(center[0], center[1]),
                max(2, int(radius * camera.scale))
            )
        
            # =========================
            # Círculo transparente
            # =========================
            radius_px = max(5, int((self.robot_radius + radius) * camera.scale))

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

            screen_pos = camera.world_to_screen(center[0], center[1])

            screen.blit(
                circle_surface,
                (screen_pos[0] - radius_px,
                screen_pos[1] - radius_px)
            )

    def set_grid_map(self, grid_map):
        self.grid_map = grid_map
        self.width = self.grid_map.width_m
        self.height = self.grid_map.height_m       
