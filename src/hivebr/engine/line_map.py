from __future__ import annotations

import os

import numpy as np
import pygame
from PIL import Image


class LineTrackMap:
    """Mapa de pista de linha (line following).

    Carrega uma imagem em tons de cinza onde a **linha preta** é a trajetória a
    ser seguida. Diferente do :class:`OccupancyGridMap`, os pixels escuros são a
    pista (livre) e os claros são o fundo (fora da linha). A imagem é usada para
    amostrar sensores analógicos (ex.: TCRT5000), retornando um valor em
    ``[0, 1]`` proporcional à "escuridão" da superfície (``1`` = linha preta,
    ``0`` = fundo branco).
    """

    def __init__(self, image_path: str, resolution: float, colors: dict = None):
        self.resolution = float(resolution)
        self.colors = colors if colors is not None else {}

        resolved_path = self._resolve_path(image_path)

        gray = np.array(Image.open(resolved_path).convert("L"), dtype=np.float32)
        self.height, self.width = gray.shape
        self.width_m = self.width * self.resolution
        self.height_m = self.height * self.resolution

        # Inverte verticalmente para alinhar a origem da imagem (topo) com a
        # origem do mundo (canto inferior esquerdo), como no occupancy grid.
        self.darkness = np.flipud(1.0 - gray / 255.0)

        try:
            self.pygame_image = pygame.transform.flip(
                pygame.image.load(resolved_path).convert(), False, True
            )
        except Exception as exc:  # pragma: no cover - depends on pygame setup
            print(f"Warning: could not load line map image in Pygame: {exc}")
            self.pygame_image = None

    @staticmethod
    def _resolve_path(image_path: str) -> str:
        if os.path.isabs(image_path) and os.path.exists(image_path):
            return image_path

        cwd_path = os.path.join(os.getcwd(), image_path)
        if os.path.exists(cwd_path):
            return cwd_path

        pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_path = os.path.join(pkg_parent, image_path)
        if os.path.exists(pkg_path):
            return pkg_path

        raise FileNotFoundError(
            f"Line map image not found at {image_path} (resolved to {cwd_path})"
        )

    def world_to_pixel(self, x: float, y: float) -> tuple[int, int]:
        """Converte coordenadas de mundo (m) para pixel ``(col, row)``."""
        col = int(x / self.resolution)
        row = self.height - 1 - int(y / self.resolution)
        return col, row

    def sample(self, x: float, y: float, aperture: float = 0.0) -> float:
        """Amostra analógica em ``(x, y)``.

        ``aperture`` é o raio (em metros) da área média em torno do ponto,
        representando o "campo de visão" do sensor. Fora do mapa retorna ``0``
        (fundo claro / fora da linha).
        """
        ix = int(x / self.resolution)
        iy = int(y / self.resolution)

        if ix < 0 or ix >= self.width or iy < 0 or iy >= self.height:
            return 0.0

        radius = int(round(aperture / self.resolution))
        if radius <= 0:
            return float(self.darkness[iy, ix])

        x0 = max(0, ix - radius)
        x1 = min(self.width, ix + radius + 1)
        y0 = max(0, iy - radius)
        y1 = min(self.height, iy + radius + 1)
        return float(self.darkness[y0:y1, x0:x1].mean())

    def is_on_line(self, x: float, y: float, threshold: float = 0.5) -> bool:
        return self.sample(x, y) >= threshold

    def draw(self, screen: pygame.Surface, camera):
        """Desenha a imagem da pista no mundo (fundo da arena)."""
        width_px = int(self.width_m * camera.scale)
        height_px = int(self.height_m * camera.scale)
        if width_px <= 0 or height_px <= 0:
            return

        sx, sy = camera.world_to_screen(0.0, self.height_m)
        if self.pygame_image is not None:
            scaled = pygame.transform.scale(self.pygame_image, (width_px, height_px))
            screen.blit(scaled, (sx, sy))

        border = self.colors.get("line_border", [0, 0, 0])
        pygame.draw.rect(screen, tuple(border), (sx, sy, width_px, height_px), 2)
