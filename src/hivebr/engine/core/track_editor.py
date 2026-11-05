from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from .line_map import LineTrackMap


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
        self.canvas: np.ndarray | None = None  # Changed from pygame.Surface to numpy array
        self._build_canvas()

        if getattr(world, "line_map", None) is not None:
            self.load_from_line_map(world.line_map)

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------
    def _build_canvas(self):
        self.width_px = max(1, int(round(self.world.width / self.resolution)))
        self.height_px = max(1, int(round(self.world.height / self.resolution)))
        # White background (255, 255, 255) - using uint8 grayscale
        self.canvas = np.full((self.height_px, self.width_px), 255, dtype=np.uint8)
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
        # Draw on numpy canvas
        cx, cy = self._last_px
        radius = max(1, self.line_px // 2)
        self._draw_circle_on_canvas(cx, cy, radius, 0)

    def extend(self, x: float, y: float):
        if not self.drawing:
            return
        px = self.world_to_canvas(x, y)
        if px != self._last_px:
            self._draw_line_on_canvas(self._last_px[0], self._last_px[1], px[0], px[1], self.line_px, 0)
            self._draw_circle_on_canvas(px[0], px[1], max(1, self.line_px // 2), 0)
            self._last_px = px
            self.stroke_world.append((float(x), float(y)))

    def end(self):
        self.drawing = False
        if len(self.stroke_world) >= 2:
            x0, y0 = self.stroke_world[0]
            x1, y1 = self.stroke_world[1]
            self.start_pose = (x0, y0, math.atan2(y1 - y0, x1 - x0))

    def clear(self):
        self.canvas.fill(255)
        self.stroke_world = []
        self.start_pose = None
        self.drawing = False
        self._last_px = None

    def _draw_circle_on_canvas(self, cx: int, cy: int, radius: int, color: int):
        """Draw a filled circle on the numpy canvas."""
        y_min = max(0, cy - radius)
        y_max = min(self.height_px, cy + radius + 1)
        x_min = max(0, cx - radius)
        x_max = min(self.width_px, cx + radius + 1)
        
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    self.canvas[y, x] = color

    def _draw_line_on_canvas(self, x0: int, y0: int, x1: int, y1: int, width: int, color: int):
        """Draw a line on the numpy canvas using Bresenham's algorithm."""
        # Bresenham's line algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        
        x, y = x0, y0
        radius = max(1, width // 2)
        
        while True:
            # Draw circle at each point for thickness
            self._draw_circle_on_canvas(x, y, radius, color)
            
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    # ------------------------------------------------------------------
    # Conversão para LineTrackMap
    # ------------------------------------------------------------------
    def _gray_array(self) -> np.ndarray:
        """Return the canvas as a grayscale array (already grayscale)."""
        return self.canvas.copy()

    def load_from_line_map(self, line_map: LineTrackMap):
        gray = line_map.to_gray()
        # gray is already (H, W) with row 0 = top
        # Our canvas is also row 0 = top (numpy array)
        self.canvas = gray.copy()
        # Resize if needed
        if self.canvas.shape != (self.height_px, self.width_px):
            from PIL import Image
            img = Image.fromarray(gray)
            img = img.resize((self.width_px, self.height_px), Image.Resampling.NEAREST)
            self.canvas = np.array(img)

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
        # Save using PIL
        from PIL import Image
        img = Image.fromarray(self.canvas, mode='L')
        img.save(str(path))

    # draw method removed - rendering is handled by frontend

    def draw_cursor_hint(self, screen):
        # Not applicable in headless mode
        pass