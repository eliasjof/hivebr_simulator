from __future__ import annotations

import heapq
import math
import numpy as np


class AStarPlanner:

    def __init__(
        self,
        bounds,
        resolution=0.25,
        robot_radius=0.25,
        connectivity=8,
    ):
        """
        bounds = (xmin, xmax, ymin, ymax)
        """
        self.bounds      = bounds
        self.resolution  = resolution
        self.robot_radius = robot_radius
        self.connectivity = connectivity

        self.xmin, self.xmax, self.ymin, self.ymax = bounds

        self.nx = int(np.ceil((self.xmax - self.xmin) / resolution))
        self.ny = int(np.ceil((self.ymax - self.ymin) / resolution))

    # =====================================================
    # WORLD <-> GRID
    # =====================================================

    def world_to_grid(self, x, y):
        """
        Converte coordenada mundo → índice de célula.
        Usa floor para garantir que o ponto caia na célula correta,
        independente de valores negativos ou limites de borda.
        """
        ix = int(math.floor((x - self.xmin) / self.resolution))
        iy = int(math.floor((y - self.ymin) / self.resolution))
        return ix, iy

    def grid_to_world(self, ix, iy):
        """Retorna o centro da célula em coordenadas mundo."""
        x = self.xmin + (ix + 0.5) * self.resolution
        y = self.ymin + (iy + 0.5) * self.resolution
        return x, y

    def _in_bounds(self, ix, iy) -> bool:
        return 0 <= ix < self.nx and 0 <= iy < self.ny

    # =====================================================
    # OCCUPANCY GRID
    # =====================================================

    def build_occupancy_grid(self, obstacles) -> np.ndarray:
        """
        Marca como bloqueada toda célula cujo CENTRO está a menos de
        (obs.radius + robot_radius) de qualquer obstáculo.

        O raio de inflação garante que o robô (aproximado por um círculo)
        nunca colida se seguir o caminho planejado.
        """
        grid = np.zeros((self.nx, self.ny), dtype=np.uint8)

        for obs in obstacles:
            inflate = obs[2] + self.robot_radius

            # Bounding box de células que o obstáculo inflado pode atingir
            ix_min = max(0, int(math.floor((obs[0] - inflate - self.xmin) / self.resolution)))
            ix_max = min(self.nx - 1, int(math.ceil ((obs[0] + inflate - self.xmin) / self.resolution)))
            iy_min = max(0, int(math.floor((obs[1] - inflate - self.ymin) / self.resolution)))
            iy_max = min(self.ny - 1, int(math.ceil ((obs[1] + inflate - self.ymin) / self.resolution)))

            for ix in range(ix_min, ix_max + 1):
                for iy in range(iy_min, iy_max + 1):
                    # Ponto da célula mais próximo do centro do obstáculo.
                    # Se esse ponto está dentro do raio inflado, a célula
                    # toca o obstáculo e deve ser bloqueada — mesmo que o
                    # centro da célula esteja fora (corrige bordas do círculo).
                    x_left  = self.xmin + ix * self.resolution
                    x_right = x_left + self.resolution
                    y_bot   = self.ymin + iy * self.resolution
                    y_top   = y_bot + self.resolution
                    nearest_x = max(x_left,  min(obs[0], x_right))
                    nearest_y = max(y_bot,   min(obs[1], y_top))
                    if math.hypot(nearest_x - obs[0], nearest_y - obs[1]) <= inflate:
                        grid[ix, iy] = 1

        return grid

    # =====================================================
    # HEURISTIC  (distância euclidiana em células)
    # =====================================================

    @staticmethod
    def heuristic(a, b) -> float:
        return math.hypot(b[0] - a[0], b[1] - a[1])

    # =====================================================
    # NEIGHBORS
    # =====================================================

    def get_neighbors(self, node):
        if self.connectivity == 4:
            motions = [(-1,0),(1,0),(0,-1),(0,1)]
        else:
            motions = [
                (-1, 0),(1, 0),(0,-1),(0, 1),
                (-1,-1),(-1, 1),(1,-1),(1, 1),
            ]
        for dx, dy in motions:
            nx_, ny_ = node[0] + dx, node[1] + dy
            if self._in_bounds(nx_, ny_):
                yield (nx_, ny_)

    # =====================================================
    # PLAN
    # =====================================================

    def plan(self, start, goal, obstacles):
        """
        Retorna (path, occ).

        path: lista de coordenadas mundo [(x,y), ...] do ponto
              imediatamente após o start até o goal, inclusive.
              Retorna None se não houver caminho.
        occ:  grade de ocupação (np.ndarray) para visualização.
        """
        occ = self.build_occupancy_grid(obstacles)

        start_idx = self.world_to_grid(*start)
        goal_idx  = self.world_to_grid(*goal)

        # Garante que start e goal estão dentro dos bounds
        if not self._in_bounds(*start_idx) or not self._in_bounds(*goal_idx):
            return None, occ

        # Se o goal estiver bloqueado, tenta a célula mais próxima livre
        if occ[goal_idx]:
            goal_idx = self._nearest_free(occ, goal_idx)
            if goal_idx is None:
                return None, occ

        open_set = []
        heapq.heappush(open_set, (0.0, start_idx))

        came_from = {}                    # nó → pai
        g_cost    = {start_idx: 0.0}

        while open_set:
            _, current = heapq.heappop(open_set)

            if current == goal_idx:
                return self._reconstruct_path(came_from, start_idx, current), occ

            for nbr in self.get_neighbors(current):
                if occ[nbr]:
                    continue

                step = math.hypot(nbr[0] - current[0], nbr[1] - current[1])
                tent_g = g_cost[current] + step

                if nbr not in g_cost or tent_g < g_cost[nbr]:
                    g_cost[nbr] = tent_g
                    f = tent_g + self.heuristic(nbr, goal_idx)
                    heapq.heappush(open_set, (f, nbr))
                    came_from[nbr] = current

        return None, occ

    # =====================================================
    # RECONSTRUCT PATH  (inclui start e goal)
    # =====================================================

    def _reconstruct_path(self, came_from, start_idx, current):
        """
        Reconstrói o caminho do start ao goal em coordenadas mundo.

        Correção em relação à versão anterior:
          - inclui o nó inicial (start_idx)
          - inclui o nó final  (current == goal_idx)
        """
        path_idx = []
        node = current
        while node in came_from:
            path_idx.append(node)
            node = came_from[node]
        path_idx.append(start_idx)   # ← nó inicial explicitamente adicionado
        path_idx.reverse()

        return [self.grid_to_world(ix, iy) for ix, iy in path_idx]

    # =====================================================
    # HELPER — célula livre mais próxima do goal
    # =====================================================

    def _nearest_free(self, occ, idx, max_radius=10):
        """BFS a partir de idx para encontrar a célula livre mais próxima."""
        from collections import deque
        visited = {idx}
        q = deque([idx])
        while q:
            ix, iy = q.popleft()
            if not occ[ix, iy]:
                return (ix, iy)
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                nb = (ix+dx, iy+dy)
                if nb not in visited and self._in_bounds(*nb):
                    visited.add(nb)
                    q.append(nb)
        return None