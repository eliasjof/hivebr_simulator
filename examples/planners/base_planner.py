"""
base_planner.py
---------------
Classe base para planejadores de caminho no hivebr.engine.

Para implementar um novo planejador, herde de BasePlanner e
implemente apenas o método `_plan(start, goal, obs_list) -> list | None`.

Exemplo mínimo
--------------
    from base_planner import BasePlanner

    class MeuPlanner(BasePlanner):
        def _plan(self, start, goal, obs_list):
            # ... sua lógica aqui ...
            return [(x1,y1), (x2,y2), ...]   # ou None se falhar

    # Uso no simulador
    p = MeuPlanner(bounds=(0,10,0,10), robot_radius=0.3)
    path, debug = p.plan(start, goal, obstacles)
"""

from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


# ──────────────────────────────────────────────────────────────
# Obstacle adapter
# ──────────────────────────────────────────────────────────────

@dataclass
class Obstacle:
    x: float
    y: float
    radius: float


def parse_obstacles(world_obstacles) -> list[Obstacle]:
    """Converte world.obstacles (np.array [cx,cy,r]) → lista de Obstacle."""
    return [Obstacle(float(o[0]), float(o[1]), float(o[2])) for o in world_obstacles]


# ──────────────────────────────────────────────────────────────
# Nó genérico de árvore / grafo
# ──────────────────────────────────────────────────────────────

@dataclass
class Node:
    x: float
    y: float
    parent: "Node | None" = field(default=None, repr=False)
    cost:   float         = 0.0   # custo acumulado do start até este nó (para RRT*)

    def dist(self, other: "Node") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def dist_xy(self, x: float, y: float) -> float:
        return math.hypot(self.x - x, self.y - y)

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


# ──────────────────────────────────────────────────────────────
# DebugData — informação de visualização retornada por plan()
# ──────────────────────────────────────────────────────────────

@dataclass
class DebugData:
    """
    Dados opcionais de debug/visualização retornados por plan().

    Cada planejador preenche os campos relevantes para ele:
      - tree_edges : arestas da árvore (RRT, RRT*)
      - graph_edges: arestas do grafo  (PRM)
      - samples    : amostras geradas  (qualquer)
    """
    tree_edges:  list[tuple] = field(default_factory=list)  # (x1,y1,x2,y2)
    graph_edges: list[tuple] = field(default_factory=list)  # (x1,y1,x2,y2)
    samples:     list[tuple] = field(default_factory=list)  # (x,y)


# ──────────────────────────────────────────────────────────────
# BasePlanner
# ──────────────────────────────────────────────────────────────

class BasePlanner(ABC):
    """
    Classe base para todos os planejadores.

    Subclasses devem implementar:
        _plan(start, goal, obs_list) -> tuple[list|None, DebugData]

    Parâmetros compartilhados
    -------------------------
    bounds       : (xmin, xmax, ymin, ymax) em metros
    robot_radius : raio de inflação dos obstáculos (m)
    seed         : semente aleatória (None = aleatório)
    """

    def __init__(
        self,
        bounds: tuple,
        robot_radius: float = 0.3,
        seed: int | None = None,
    ):
        self.xmin, self.xmax, self.ymin, self.ymax = bounds
        self.robot_radius = robot_radius
        self.rng = random.Random(seed)

    # ── interface pública ──────────────────────────────────────

    def plan(
        self,
        start: tuple,
        goal:  tuple,
        obstacles,                    # world.obstacles (np.arrays)
        occupancy_map=None,
    ) -> tuple[list | None, DebugData]:
        """
        Planeja um caminho de start até goal.

        Retorna
        -------
        path      : lista de (x, y) do start ao goal, ou None se falhar.
        debug     : DebugData com informação de visualização.
        """
        obs_list = parse_obstacles(obstacles)
        return self._plan(
            (float(start[0]), float(start[1])),
            (float(goal[0]),  float(goal[1])),
            obs_list,
            occupancy_map=occupancy_map,
        )

    @abstractmethod
    def _plan(
        self,
        start:    tuple[float, float],
        goal:     tuple[float, float],
        obs_list: list[Obstacle],
        occupancy_map=None,
    ) -> tuple[list | None, DebugData]:
        """Implementar na subclasse."""
        ...

    # ── helpers de colisão (disponíveis para todas as subclasses) ──

    def _point_free(self, x: float, y: float, obs_list: list[Obstacle], occupancy_map=None) -> bool:
        """True se o ponto (x,y) está livre de colisão."""
        if occupancy_map and occupancy_map.is_occupied(x, y, use_inflated=True):
            return False
            
        return all(
            math.hypot(x - o.x, y - o.y) >= o.radius + self.robot_radius
            for o in obs_list
        )

    def _segment_free(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        obs_list: list[Obstacle],
        occupancy_map=None,
    ) -> bool:
        """True se o segmento p1→p2 não colide com nenhum obstáculo."""
        # Se houver occupancy map, verificamos colisão ao longo do segmento (amostragem simples)
        if occupancy_map:
            steps = 20 # resolução da verificação
            for i in range(steps + 1):
                t = i / steps
                x = p1[0] + (p2[0] - p1[0]) * t
                y = p1[1] + (p2[1] - p1[1]) * t
                if occupancy_map.is_occupied(x, y, use_inflated=True):
                    return False
        
        return all(
            not self._segment_hits_circle(p1, p2, o)
            for o in obs_list
        )

    def _segment_hits_circle(
        self,
        p1: tuple,
        p2: tuple,
        obs: Obstacle,
    ) -> bool:
        inflate = obs.radius + self.robot_radius
        dx, dy  = p2[0] - p1[0], p2[1] - p1[1]
        fx, fy  = p1[0] - obs.x,  p1[1] - obs.y
        a = dx*dx + dy*dy
        if a < 1e-12:
            return math.hypot(fx, fy) <= inflate
        b = 2*(fx*dx + fy*dy)
        c = fx*fx + fy*fy - inflate*inflate
        disc = b*b - 4*a*c
        if disc < 0:
            return False
        sq   = math.sqrt(disc)
        t1   = (-b - sq) / (2*a)
        t2   = (-b + sq) / (2*a)
        return (0 <= t1 <= 1) or (0 <= t2 <= 1) or (t1 < 0 < t2)

    # ── helpers geométricos ────────────────────────────────────

    def _in_bounds(self, x: float, y: float) -> bool:
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax

    def _random_sample(self) -> tuple[float, float]:
        return (
            self.rng.uniform(self.xmin, self.xmax),
            self.rng.uniform(self.ymin, self.ymax),
        )

    def _steer(
        self,
        from_node: Node,
        tx: float,
        ty: float,
        step_size: float,
    ) -> tuple[float, float]:
        """Move de from_node em direção a (tx,ty) no máximo step_size."""
        dx, dy = tx - from_node.x, ty - from_node.y
        dist   = math.hypot(dx, dy)
        if dist <= step_size:
            return tx, ty
        return from_node.x + dx/dist*step_size, from_node.y + dy/dist*step_size

    @staticmethod
    def _nearest(nodes: list[Node], x: float, y: float) -> Node:
        return min(nodes, key=lambda n: n.dist_xy(x, y))

    @staticmethod
    def _reconstruct_path(goal_node: Node) -> list[tuple[float, float]]:
        path, node = [], goal_node
        while node is not None:
            path.append(node.as_tuple())
            node = node.parent
        path.reverse()
        return path

    @staticmethod
    def _build_tree_edges(nodes: list[Node]) -> list[tuple]:
        return [
            (n.parent.x, n.parent.y, n.x, n.y)
            for n in nodes if n.parent is not None
        ]
