from __future__ import annotations

import math
import numpy as np
from pathlib import Path

from .config import DEFAULT_CONFIG


class World:
    """Simulation world - physics and collision only, no rendering."""
    
    def __init__(self, config: dict):
        self.config = config
        self.width = float(config["world"]["width"])
        self.height = float(config["world"]["height"])

        self.grid_size = float(
            config["world"].get("grid_size", 1.0)
        )

        self.resolution = float(
            config["world"].get("resolution", 0.1)
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

        self.obstacles = []

        for obs in config["world"].get("obstacles", []):
            self.obstacles.append(
                self._parse_obstacle(obs)
            )

        # Recarga places
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

        self.line_map = None
        if config["world"].get("line_map_image"):
            self.load_line_map(
                config["world"]["line_map_image"],
                float(config["world"].get("resolution", 0.1)),
            )

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

    def load_line_map(self, image_path: str, resolution: float):
        """Carrega dinamicamente uma pista de linha (imagem preto no branco)."""
        from .line_map import LineTrackMap
        self.line_map = LineTrackMap(
            image_path=image_path,
            resolution=float(resolution),
            colors=self.colors,
        )
        self.width = self.line_map.width_m
        self.height = self.line_map.height_m
        self.resolution = self.line_map.resolution

    def set_line_map(self, line_map):
        """Instala um :class:`LineTrackMap` já construído (ex.: desenhado na UI)."""
        self.line_map = line_map
        self.width = line_map.width_m
        self.height = line_map.height_m
        self.resolution = line_map.resolution

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

    def get_recharge_place(self, id):
        if 0 <= id < len(self.recharge_places):
            return self.get_position(self.recharge_places[id])
        return None

    # ======================================================
    # Métodos de rendering removidos - apenas lógica pura
    # ======================================================
    # draw_grid, draw_origin, draw_axes, draw_recharge_places, 
    # draw_obstacles, draw_line_map - todos removidos
    # O rendering é responsabilidade do frontend (Canvas/WebGL)