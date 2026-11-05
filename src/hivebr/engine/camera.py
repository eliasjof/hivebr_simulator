from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class Camera2D:
    world_width: float
    world_height: float
    viewport_width: int
    viewport_height: int
    initial_zoom: float = 1.0
    min_zoom: float = 0.25
    max_zoom: float = 8.0
    zoom_step: float = 1.1
    margin_x: float = 1.0
    margin_y: float = 1.0

    def __post_init__(self):
        self.zoom = self.initial_zoom
        self.offset = np.array([-self.margin_x, -self.margin_y], dtype=float)
        self.compute_scale()

    def compute_scale(self):
        scale_x = self.viewport_width / self.world_width
        scale_y = self.viewport_height / self.world_height
        self.base_scale = min(scale_x, scale_y)
        self.scale = self.base_scale * self.zoom

    def resize(self, viewport_width: int, viewport_height: int):
        self.viewport_width = max(1, int(viewport_width))
        self.viewport_height = max(1, int(viewport_height))
        self.compute_scale()

    def reset(self):
        self.zoom = self.initial_zoom
        self.offset = np.array([-self.margin_x, -self.margin_y], dtype=float)
        self.compute_scale()

    def center_on_origin_with_margin(self):
        self.offset = np.array([-self.margin_x, -self.margin_y], dtype=float)

    def center_on_rect(self, center_x: float, center_y: float, width: float, height: float, margin: float = 0.5):
        """Centraliza a câmera em um retângulo (ex: pista de linha) com margem.
        
        Args:
            center_x, center_y: Centro do retângulo em coordenadas de mundo
            width, height: Dimensões do retângulo
            margin: Margem extra em metros ao redor do retângulo
        """
        # Calcula o zoom necessário para caber o retângulo + margem na viewport
        target_w = width + 2 * margin
        target_h = height + 2 * margin
        
        scale_x = self.viewport_width / target_w
        scale_y = self.viewport_height / target_h
        needed_scale = min(scale_x, scale_y)
        
        # Converte para zoom relativo ao base_scale
        needed_zoom = needed_scale / self.base_scale
        
        # Limita ao range de zoom
        needed_zoom = float(np.clip(needed_zoom, self.min_zoom, self.max_zoom))
        
        self.zoom = needed_zoom
        self.compute_scale()
        
        # Calcula offset para centralizar o retângulo na viewport
        # world_to_screen(center_x, center_y) deve dar (viewport_width/2, viewport_height/2)
        # sx = (center_x - offset_x) * scale + ox = viewport_width/2
        # sy = viewport_height - (center_y - offset_y) * scale - oy = viewport_height/2
        ox = (self.viewport_width - self.world_width * self.scale) / 2
        oy = (self.viewport_height - self.world_height * self.scale) / 2
        
        offset_x = center_x + (ox - self.viewport_width / 2) / self.scale
        offset_y = center_y + (oy - self.viewport_height / 2) / self.scale
        
        self.offset = np.array([offset_x, offset_y], dtype=float)

    def zoom_at(self, mouse_pos, wheel_y: int):
        old_world = self.screen_to_world(*mouse_pos)
        factor = self.zoom_step if wheel_y > 0 else 1.0 / self.zoom_step
        self.zoom = float(np.clip(self.zoom * factor, self.min_zoom, self.max_zoom))
        self.compute_scale()
        new_world = self.screen_to_world(*mouse_pos)
        self.offset += old_world - new_world

    def pan_pixels(self, dx: float, dy: float):
        self.offset[0] -= dx / self.scale
        self.offset[1] += dy / self.scale

    def _display_offsets(self):
        ox = (self.viewport_width - self.world_width * self.scale) / 2
        oy = (self.viewport_height - self.world_height * self.scale) / 2
        return ox, oy

    def world_to_screen(self, px: float, py: float):
        ox, oy = self._display_offsets()
        px_cam = px - self.offset[0]
        py_cam = py - self.offset[1]
        sx = int(px_cam * self.scale + ox)
        sy = int(self.viewport_height - (py_cam * self.scale + oy))
        return sx, sy

    def screen_to_world(self, sx: float, sy: float):
        ox, oy = self._display_offsets()
        px = (sx - ox) / self.scale + self.offset[0]
        py = ((self.viewport_height - sy) - oy) / self.scale + self.offset[1]
        return np.array([px, py], dtype=float)
