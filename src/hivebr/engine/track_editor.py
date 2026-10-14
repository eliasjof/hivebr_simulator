from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pygame

from hivebr.engine.line_map import LineTrackMap


class TrackEditor:
    """Editor interativo de pista para o seguidor de linha.

    Mantém um *canvas* (uma imagem em tons de cinza, fundo branco) em
    coordenadas de mundo. Com o modo de desenho ativo, o usuário traça a linha
    preta com o botão esquerdo do mouse; :meth:`apply` converte o desenho em um
    :class:`LineTrackMap` e o instala no mundo (``world.line_map``), de modo que
    os sensores do robô passam a segui-lo.
    """

    def __init__(self, world, config: dict):
        self.world = world
        self.config = config
        self.resolution = float(
            getattr(world, "resolution", config.get("world", {}).get("resolution", 0.1))
        )
        self.line_width_m = float(config.get("robot", {}).get("line_width", 0.02))

        self.active = False
        self.drawing = False
        self._last_px = None
        self.stroke_world: list[tuple[float, float]] = []
        self.start_pose: tuple[float, float, float] | None = None

        self.width_px = 0
        self.height_px = 0
        self.line_px = 0
        self.canvas: pygame.Surface | None = None
        self._build_canvas()

        if getattr(world, "line_map", None) is not None:
            self.load_from_line_map(world.line_map)

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------
    def _build_canvas(self):
        self.width_px = max(1, int(round(self.world.width / self.resolution)))
        self.height_px = max(1, int(round(self.world.height / self.resolution)))
        self.canvas = pygame.Surface((self.width_px, self.height_px))
        self.canvas.fill((255, 255, 255))
        self.line_px = max(1, int(round(self.line_width_m / self.resolution)))

    @property
    def has_content(self) -> bool:
        return bool(self.stroke_world)

    def world_to_canvas(self, x: float, y: float) -> tuple[int, int]:
        col = int(round(x / self.resolution))
        row = self.height_px - 1 - int(round(y / self.resolution))
        col = max(0, min(self.width_px - 1, col))
        row = max(0, min(self.height_px - 1, row))
        return col, row

    # ------------------------------------------------------------------
    # Desenho (chamado pelo Simulator durante os eventos do mouse)
    # ------------------------------------------------------------------
    def begin(self, x: float, y: float):
        self.drawing = True
        self._last_px = self.world_to_canvas(x, y)
        self.stroke_world = [(float(x), float(y))]
        pygame.draw.circle(self.canvas, (0, 0, 0), self._last_px, max(1, self.line_px // 2))

    def extend(self, x: float, y: float):
        if not self.drawing:
            return
        px = self.world_to_canvas(x, y)
        if px != self._last_px:
            pygame.draw.line(self.canvas, (0, 0, 0), self._last_px, px, self.line_px)
            pygame.draw.circle(self.canvas, (0, 0, 0), px, max(1, self.line_px // 2))
            self._last_px = px
            self.stroke_world.append((float(x), float(y)))

    def end(self):
        self.drawing = False
        if len(self.stroke_world) >= 2:
            x0, y0 = self.stroke_world[0]
            x1, y1 = self.stroke_world[1]
            self.start_pose = (x0, y0, math.atan2(y1 - y0, x1 - x0))

    def clear(self):
        self.canvas.fill((255, 255, 255))
        self.stroke_world = []
        self.start_pose = None
        self.drawing = False
        self._last_px = None

    # ------------------------------------------------------------------
    # Conversão para LineTrackMap
    # ------------------------------------------------------------------
    def _gray_array(self) -> np.ndarray:
        raw = pygame.image.tostring(self.canvas, "RGB")
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(self.height_px, self.width_px, 3)
        return arr[:, :, 0].copy()

    def load_from_line_map(self, line_map: LineTrackMap):
        gray = line_map.to_gray()
        rgb = np.ascontiguousarray(np.repeat(gray[:, :, None], 3, axis=2))
        surface = pygame.image.frombuffer(
            rgb.tobytes(), (gray.shape[1], gray.shape[0]), "RGB"
        )
        self.canvas = pygame.transform.scale(
            surface, (self.width_px, self.height_px)
        ).copy()

    def build_line_map(self) -> LineTrackMap:
        return LineTrackMap.from_gray(self._gray_array(), self.resolution, self.world.colors)

    def apply(self, path: str | None = None) -> LineTrackMap:
        line_map = self.build_line_map()
        self.world.set_line_map(line_map)
        if path is not None:
            self.save(path)
        return line_map

    def save(self, path: str):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(self.canvas, str(path))

    # ------------------------------------------------------------------
    # Renderização
    # ------------------------------------------------------------------
    def draw(self, screen: pygame.Surface, camera):
        width_px = int(self.width_px * self.resolution * camera.scale)
        height_px = int(self.height_px * self.resolution * camera.scale)
        if width_px <= 0 or height_px <= 0:
            return
        sx, sy = camera.world_to_screen(0.0, self.height_px * self.resolution)
        scaled = pygame.transform.scale(self.canvas, (width_px, height_px))
        screen.blit(scaled, (sx, sy))

    def draw_cursor_hint(self, screen: pygame.Surface):
        font = pygame.font.SysFont("consolas", 18)
        text = font.render(
            "DRAW TRACK: arraste com o botao esquerdo | botao 'Apply Track' para seguir",
            True,
            (255, 220, 120),
        )
        padding = 6
        rect = pygame.Rect(5, 40, text.get_width() + 2 * padding, text.get_height() + 2 * padding)
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (rect.x, rect.y))
        screen.blit(text, (rect.x + padding, rect.y + padding))
