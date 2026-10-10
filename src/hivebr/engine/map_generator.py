import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation


class MapGenerator:

    @staticmethod
    def _disk_kernel(radius):
        if radius <= 0:
            return np.array([[True]])

        y, x = np.ogrid[
            -radius:radius + 1,
            -radius:radius + 1
        ]
        return x**2 + y**2 <= radius**2

    # ------------------------------------------------------------
    # GERAÇÃO DE OBSTÁCULOS
    # ------------------------------------------------------------
    @staticmethod
    def _generate_shapes(
        width,
        height,
        density,
        resolution,
        rng,
        shape_type="rect",
        min_size=10,
        max_size=30,
        max_attempts=2000
    ):
        grid = np.zeros((height, width), dtype=bool)
        obstacles = []
        target_cells = int(density * width * height)
        occupied = 0
        attempts = 0

        while occupied < target_cells and attempts < max_attempts:
            attempts += 1
            if shape_type == "rect":
                rw = rng.integers(min_size, max_size + 1)
                rh = rng.integers(min_size, max_size + 1)
                x = rng.integers(0, width - rw)
                y = rng.integers(0, height - rh)
                region = grid[y:y+rh, x:x+rw]
                if region.mean() > 0.15: continue
                grid[y:y+rh, x:x+rw] = True
                obstacles.append({
                    'type': 'rect', 
                    'x': (x + rw/2) * resolution, 
                    'y': (height - (y + rh/2)) * resolution, 
                    'w': rw * resolution, 
                    'h': rh * resolution
                })
            else: # circle
                r = rng.integers(min_size // 2, max_size // 2 + 1)
                x = rng.integers(r, width - r)
                y = rng.integers(r, height - r)
                y_grid, x_grid = np.ogrid[:height, :width]
                mask = (x_grid - x)**2 + (y_grid - y)**2 <= r**2
                if np.sum(grid[mask]) / np.sum(mask) > 0.3: continue
                grid[mask] = True
                obstacles.append({
                    'type': 'circle', 
                    'x': float(x * resolution), 
                    'y': float((height - y) * resolution), 
                    'r': float(r * resolution)
                })
            occupied = np.count_nonzero(grid)
        return grid, obstacles



    @staticmethod
    def _generate_benchmark_map(
        width,
        height,
        rng,
        n_walls=25,
        wall_thickness=2,
        min_wall_length=20,
    ):
        grid = np.zeros((height, width), dtype=bool)

        for _ in range(n_walls):

            horizontal = rng.random() < 0.5

            if horizontal:

                length = rng.integers(
                    min_wall_length,
                    width // 2
                )

                x = rng.integers(
                    1,
                    width - length - 1
                )

                y = rng.integers(
                    5,
                    height - 5
                )

                grid[
                    y:y + wall_thickness,
                    x:x + length
                ] = True

                # cria uma passagem
                if length > 10:

                    door_size = rng.integers(3, 8)

                    door_x = rng.integers(
                        x + 3,
                        x + length - door_size - 3
                    )

                    grid[
                        y:y + wall_thickness,
                        door_x:door_x + door_size
                    ] = False

            else:

                length = rng.integers(
                    min_wall_length,
                    height // 2
                )

                x = rng.integers(
                    5,
                    width - 5
                )

                y = rng.integers(
                    1,
                    height - length - 1
                )

                grid[
                    y:y + length,
                    x:x + wall_thickness
                ] = True

                # cria uma passagem
                if length > 10:

                    door_size = rng.integers(3, 8)

                    door_y = rng.integers(
                        y + 3,
                        y + length - door_size - 3
                    )

                    grid[
                        door_y:door_y + door_size,
                        x:x + wall_thickness
                    ] = False

        return grid
    # ------------------------------------------------------------
    # FUNÇÃO PRINCIPAL
    # ------------------------------------------------------------
    @staticmethod
    def create_grid(
        width=100,
        height=100,
        seed=None,
        obstacle_rate=0.25,
        robot_radius=0.0,
        resolution=1.0,
        max_iter=20,
        tolerance=0.01,
        min_size=10,
        max_size=30,
        n_walls=25,
        wall_thickness=2,
        min_wall_length=20,
        border=True,
        type="U",
        shape_type="rect"
    ):
        grid = np.zeros((height, width), dtype=bool)
        if type == 'U':
            grid[10:90, 10:20] = True # Esquerda
            grid[10:90, 80:90] = True # Direita
            grid[80:90, 20:80] = True # Base
            return grid, []
        elif type == 'L':
            grid[10:90, 10:20] = True # Esquerda
            grid[80:90, 20:90] = True # Base
            return grid, []
        

        elif type == 'benchmark':

            rng = np.random.default_rng(seed)

            grid = MapGenerator._generate_benchmark_map(
                width,
                height,
                rng,
                n_walls=n_walls,
                wall_thickness=wall_thickness,
                min_wall_length=min_wall_length
            )

            if border:
                grid[0, :] = True
                grid[-1, :] = True
                grid[:, 0] = True
                grid[:, -1] = True
            
            return grid, [] # Benchmark não retorna lista de obstáculos detalhada no momento
        else:
            rng = np.random.default_rng(seed)

            radius = int(np.ceil(robot_radius / resolution))
            kernel = MapGenerator._disk_kernel(radius)

            # chute inicial (IMPORTANTE: menor que obstacle_rate)
            density = obstacle_rate * 0.4

            best = None
            best_obstacles = []
            best_err = 1e9

            for _ in range(max_iter):

                raw, current_obstacles = MapGenerator._generate_shapes(
                    width,
                    height,
                    density,
                    resolution,
                    rng,
                    shape_type=shape_type,
                    min_size=min_size,
                    max_size=max_size
                )

                inflated = binary_dilation(raw, structure=kernel)

                occ = inflated.mean()
                err = abs(occ - obstacle_rate)

                if err < best_err:
                    best_err = err
                    best = inflated.copy()
                    best_obstacles = current_obstacles

                if err < tolerance:
                    break

                # ajuste estável (evita explosão)
                if occ > obstacle_rate:
                    density *= 0.85
                else:
                    density *= 1.10

                density = np.clip(density, 0.01, 0.60)

            grid = best

            # bordas (muito importante para planning benchmark)
            if border:
                grid[0, :] = True
                grid[-1, :] = True
                grid[:, 0] = True
                grid[:, -1] = True

        return grid, best_obstacles

    # ------------------------------------------------------------
    @staticmethod
    def save(grid, path):
        img = (np.logical_not(np.flipud(grid)) * 255).astype(np.uint8)
        Image.fromarray(img).save(path)