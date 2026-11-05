from __future__ import annotations

import os

import numpy as np
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

        # self.pygame_image = None  # REMOVED for core

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

    # draw method removed - rendering is handled by frontend

    def to_gray(self) -> np.ndarray:
        """Retorna a imagem em tons de cinza (``uint8``, linha 0 no topo)."""
        return np.flipud((1.0 - self.darkness) * 255.0).astype(np.uint8)

    @classmethod
    def from_gray(cls, gray: np.ndarray, resolution: float, colors: dict = None):
        """Cria um mapa de linha a partir de um array ``uint8`` (H, W).

        A linha 0 do array corresponde ao topo da imagem (maior ``y`` do
        mundo), como em uma imagem lida do disco.
        """
        instance = cls.__new__(cls)
        instance.resolution = float(resolution)
        instance.colors = colors if colors is not None else {}

        gray = np.asarray(gray, dtype=np.uint8)
        if gray.ndim == 3:
            gray = gray[:, :, 0]
        instance.height, instance.width = gray.shape
        instance.width_m = instance.width * instance.resolution
        instance.height_m = instance.height * instance.resolution
        instance.darkness = np.flipud(1.0 - gray.astype(np.float32) / 255.0)

        # instance.pygame_image = None  # REMOVED for core

        return instance