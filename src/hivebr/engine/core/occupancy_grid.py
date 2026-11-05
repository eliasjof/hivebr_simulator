from __future__ import annotations
import os
import math
import numpy as np


def _binary_dilation(grid: np.ndarray, structure: np.ndarray, iterations: int) -> np.ndarray:
    """Binary dilation that works with or without SciPy.

    Uses ``scipy.ndimage.binary_dilation`` when available; otherwise falls
    back to a pure-NumPy implementation (3x3 neighbourhood max-filter), so
    the simulator can run in WASM/Pyodide without the heavy SciPy package.
    Only the 3x3 (or smaller) structuring element used by this module is
    supported by the fallback.
    """
    try:
        from scipy.ndimage import binary_dilation as _scipy_dilate
        return _scipy_dilate(grid, structure=structure, iterations=iterations)
    except Exception:
        result = np.asarray(grid, dtype=bool).copy()
        if iterations <= 0:
            return result
        for _ in range(iterations):
            padded = np.pad(result, 1, mode="constant", constant_values=False)
            dilated = np.zeros_like(result)
            for dy in range(3):
                for dx in range(3):
                    # Skip offsets disabled in the structuring element.
                    if not structure[dy, dx]:
                        continue
                    dilated |= padded[dy:dy + result.shape[0], dx:dx + result.shape[1]]
            result = dilated
        return result


class OccupancyGridMap:
    def __init__(self, image_path: str, resolution: float, robot_radius: float = None, colors: dict = None):
        """
        Initializes the Occupancy Grid Map from an image.
        """
        self.resolution = float(resolution)
        self.colors = colors if colors is not None else {
            "occupancy_inflated": [220, 50, 50],
            "occupancy_raw": [50, 100, 255]
        }
        
        # Resolve image path
        resolved_path = image_path
        if not os.path.isabs(image_path):
            cwd_path = os.path.join(os.getcwd(), image_path)
            if os.path.exists(cwd_path):
                resolved_path = cwd_path
            else:
                pkg_parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                pkg_path = os.path.join(pkg_parent, image_path)
                if os.path.exists(pkg_path):
                    resolved_path = pkg_path

        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"Map image not found at {image_path} (resolved to {resolved_path})")

        # Load image and convert to grayscale (Pillow imported lazily)
        from PIL import Image
        img = Image.open(resolved_path).convert("L")
        
        # Grid array: True = occupied/obstacle (dark pixels < 128), False = free
        # FLIP VERTICALLY to align PIL/Image coordinates (0,0 top-left) with World (0,0 bottom-left)
        self.grid = np.flipud(np.array(img) < 128)
        self.height, self.width = self.grid.shape
        
        # Dimensions in meters
        self.width_m = self.width * self.resolution
        self.height_m = self.height * self.resolution
        
        # Inflated grid for collision checking
        self.inflated_grid = self.grid.copy()
        self.robot_radius = robot_radius
        if robot_radius is not None and robot_radius > 0:
            self.inflate(robot_radius)
            
        # Pygame image for fast rendering - REMOVED for core
        # self.pygame_image = None
        # self._inflated_surface = None

    def inflate(self, robot_radius: float):
        """
        Inflates the obstacles by dilating them using the robot's radius.
        Adds a small safety margin to prevent corner-cutting issues.
        """
        self.robot_radius = robot_radius
        # Adiciona uma margem de segurança de 5cm (0.05m) para evitar quinas
        safety_margin = 0.05
        inflation_cells = int(np.ceil((robot_radius + safety_margin) / self.resolution))
        
        if inflation_cells > 0:
            # Estrutura com conectividade 8 (inclui diagonais) para evitar passagens falsas nas quinas
            structure = np.ones((3, 3), dtype=bool)
            self.inflated_grid = _binary_dilation(self.grid, structure=structure, iterations=inflation_cells)
        else:
            self.inflated_grid = self.grid.copy()
        # self._inflated_surface = None # Reset cached surface

    def add_obstacle(self, x, y, radius):
        """
        Adiciona um obstáculo circular diretamente na grade de ocupação.
        """
        px = int(x / self.resolution)
        py = int(y / self.resolution)
        rad_px = int(np.ceil(radius / self.resolution))
        
        for ix in range(max(0, px - rad_px), min(self.width, px + rad_px + 1)):
            for iy in range(max(0, py - rad_px), min(self.height, py + rad_px + 1)):
                if np.sqrt((ix - px)**2 + (iy - py)**2) <= rad_px:
                    self.grid[iy, ix] = True
                    
        # Re-inflate
        self.inflate(self.robot_radius)
        # self._inflated_surface = None

    def world_to_grid(self, x: float, y: float) -> tuple[int, int]:
        """
        Converts world coordinates (x, y) to grid coordinates (ix, iy).
        World origin (0,0) is bottom-left. Image origin is top-left.
        With np.flipud applied, the grid now matches the world orientation.
        """
        ix = int(x / self.resolution)
        iy = int(y / self.resolution)
        # Check bounds
        ix = np.clip(ix, 0, self.width - 1)
        iy = np.clip(iy, 0, self.height - 1)
        return ix, iy

    def grid_to_world(self, ix: int, iy: int) -> tuple[float, float]:
        """
        Converts grid coordinates (ix, iy) to world coordinates (x, y).
        """
        x = (ix + 0.5) * self.resolution
        y = (iy + 0.5) * self.resolution
        return x, y

    def is_occupied(self, x: float, y: float, use_inflated: bool = False) -> bool:
        """
        Checks if the given world coordinates (x, y) are occupied.
        """
        ix, iy = self.world_to_grid(x, y)
        if ix < 0 or ix >= self.width or iy < 0 or iy >= self.height:
            return True  # Out of bounds is considered occupied
        
        grid_to_use = self.inflated_grid if use_inflated else self.grid
        return bool(grid_to_use[iy, ix])

    def cast_ray(self, start_x: float, start_y: float, angle: float, max_range: float) -> tuple[float, np.ndarray]:
        """
        Casts a ray into the grid map using DDA algorithm for precise collision.
        """
        dx = math.cos(angle)
        dy = math.sin(angle)
        
        # Posição inicial no grid
        ix, iy = self.world_to_grid(start_x, start_y)
        
        # Direção do incremento
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        
        # Distância para o próximo limite de célula
        t_delta_x = abs(self.resolution / dx) if dx != 0 else float('inf')
        t_delta_y = abs(self.resolution / dy) if dy != 0 else float('inf')
        
        # Distância inicial até a borda da célula atual
        # Current cell world boundaries
        cur_x_min = ix * self.resolution
        cur_x_max = (ix + 1) * self.resolution
        cur_y_min = iy * self.resolution
        cur_y_max = (iy + 1) * self.resolution
        
        t_max_x = ((cur_x_max if dx > 0 else cur_x_min) - start_x) / dx if dx != 0 else float('inf')
        t_max_y = ((cur_y_max if dy > 0 else cur_y_min) - start_y) / dy if dy != 0 else float('inf')
        
        t = 0.0
        while t < max_range:
            if t_max_x < t_max_y:
                t = t_max_x
                ix += step_x
                t_max_x += t_delta_x
            else:
                t = t_max_y
                iy += step_y
                t_max_y += t_delta_y
            
            # Checa colisão
            if 0 <= ix < self.width and 0 <= iy < self.height:
                if self.grid[iy, ix]: 
                    hit_dist = min(t, max_range)
                    return hit_dist, np.array([start_x + dx * hit_dist, start_y + dy * hit_dist])
            else:
                break # Saiu do mapa
                
        return max_range, np.array([start_x + dx * max_range, start_y + dy * max_range])

    @classmethod
    def from_grid(cls, grid, resolution, robot_radius=None, colors=None):
        instance = cls.__new__(cls)
        # Flip para alinhar com o sistema de coordenadas do mundo (y=0 na base)
        instance.grid = np.flipud(grid) 
        instance.height, instance.width = instance.grid.shape
        instance.resolution = float(resolution)
        instance.width_m = instance.width * instance.resolution
        instance.height_m = instance.height * instance.resolution
        instance.colors = colors if colors else {"occupancy_inflated": [220, 50, 50], "occupancy_raw": [50, 100, 255]}
        instance.robot_radius = robot_radius
        # instance.pygame_image = None # Sem imagem de arquivo
        
        instance.inflated_grid = instance.grid.copy()
        if robot_radius is not None and robot_radius > 0:
            instance.inflate(robot_radius)
        else:
            # instance._inflated_surface = None
            pass
        return instance

    # draw method removed - rendering is handled by frontend