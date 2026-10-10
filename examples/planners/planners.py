"""
planners.py
-----------
Implementações de planejadores usando BasePlanner.

Cada classe implementa apenas _plan() — toda a infraestrutura
(colisão, bounds, helpers) vem da BasePlanner.

Planners disponíveis
--------------------
    RRTPlanner          RRT clássico
    RRTStarPlanner      RRT* (assintoticamente ótimo)
    PRMPlanner          PRM (Probabilistic Roadmap)
    BITStarPlanner      BIT* (Batch Informed Trees)
"""

from __future__ import annotations

import math
import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from planners.base_planner import BasePlanner, Node, DebugData, Obstacle


# ══════════════════════════════════════════════════════════════
#  RRT
# ══════════════════════════════════════════════════════════════

class RRTPlanner(BasePlanner):
    """
    RRT — Rapidly-exploring Random Tree (LaValle, 1998).

    Parâmetros
    ----------
    step_size        : comprimento máximo de cada aresta (m)
    max_iter         : número máximo de iterações
    goal_sample_rate : prob. de amostrar o goal diretamente [0, 1]
    goal_tolerance   : distância para declarar que chegou ao goal (m)
    """

    def __init__(self, bounds, robot_radius=0.3, seed=None,
                 step_size=0.5, max_iter=2000,
                 goal_sample_rate=0.1, goal_tolerance=0.5):
        super().__init__(bounds, robot_radius, seed)
        self.step_size        = step_size
        self.max_iter         = max_iter
        self.goal_sample_rate = goal_sample_rate
        self.goal_tolerance   = goal_tolerance

    def _plan(self, start, goal, obs_list, occupancy_map=None):
        gx, gy  = goal
        root    = Node(*start)
        nodes   = [root]

        for _ in range(self.max_iter):

            # 1. Amostra
            if self.rng.random() < self.goal_sample_rate:
                rx, ry = gx, gy
            else:
                rx, ry = self._random_sample()

            # 2. Nó mais próximo
            nearest = self._nearest(nodes, rx, ry)

            # 3. Avança step_size em direção à amostra
            nx, ny = self._steer(nearest, rx, ry, self.step_size)

            # 4. Verifica colisão
            if not self._in_bounds(nx, ny):
                continue
            if not self._point_free(nx, ny, obs_list, occupancy_map=occupancy_map):
                continue
            if not self._segment_free(nearest.as_tuple(), (nx, ny), obs_list, occupancy_map=occupancy_map):
                continue

            new_node = Node(nx, ny, parent=nearest)
            nodes.append(new_node)

            # 5. Chegou ao goal?
            if new_node.dist_xy(gx, gy) <= self.goal_tolerance:
                if self._segment_free((nx, ny), goal, obs_list, occupancy_map=occupancy_map):
                    goal_node = Node(*goal, parent=new_node)
                    nodes.append(goal_node)
                    path  = self._reconstruct_path(goal_node)
                    debug = DebugData(tree_edges=self._build_tree_edges(nodes))
                    return path, debug

        debug = DebugData(tree_edges=self._build_tree_edges(nodes))
        return None, debug


# ══════════════════════════════════════════════════════════════
#  RRT*
# ══════════════════════════════════════════════════════════════

class RRTStarPlanner(BasePlanner):
    """
    RRT* — Karaman & Frazzoli, 2011.

    Diferenças em relação ao RRT:
      - Ao inserir um novo nó, escolhe o pai com menor custo
        dentro de um raio de rewire.
      - Após inserir, "reconecta" vizinhos se o novo nó oferece
        caminho mais curto.

    Parâmetros
    ----------
    step_size      : comprimento máximo de cada aresta (m)
    max_iter       : número máximo de iterações
    rewire_radius  : raio de busca para rewire (m)
    goal_sample_rate / goal_tolerance : igual ao RRT
    """

    def __init__(self, bounds, robot_radius=0.3, seed=None,
                 step_size=0.5, max_iter=2000, rewire_radius=1.0,
                 goal_sample_rate=0.1, goal_tolerance=0.5):
        super().__init__(bounds, robot_radius, seed)
        self.step_size        = step_size
        self.max_iter         = max_iter
        self.rewire_radius    = rewire_radius
        self.goal_sample_rate = goal_sample_rate
        self.goal_tolerance   = goal_tolerance

    def _nearby(self, nodes: list[Node], x, y, radius) -> list[Node]:
        return [n for n in nodes if n.dist_xy(x, y) <= radius]

    def _plan(self, start, goal, obs_list, occupancy_map=None):
        gx, gy    = goal
        root      = Node(*start, cost=0.0)
        nodes     = [root]
        best_goal: Node | None = None

        for _ in range(self.max_iter):

            # 1. Amostra
            if self.rng.random() < self.goal_sample_rate:
                rx, ry = gx, gy
            else:
                rx, ry = self._random_sample()

            # 2. Nó mais próximo e steer
            nearest  = self._nearest(nodes, rx, ry)
            nx, ny   = self._steer(nearest, rx, ry, self.step_size)            

            if not self._in_bounds(nx, ny):
                continue
            if not self._point_free(nx, ny, obs_list, occupancy_map=occupancy_map):
                continue
            if not self._segment_free(nearest.as_tuple(), (nx, ny), obs_list, occupancy_map=occupancy_map):
                continue

            # 3. Escolhe o pai com menor custo dentro do rewire_radius
            neighbors = self._nearby(nodes, nx, ny, self.rewire_radius)
            best_parent = nearest
            best_cost   = nearest.cost + math.hypot(nx - nearest.x, ny - nearest.y)

            for nb in neighbors:
                c = nb.cost + math.hypot(nx - nb.x, ny - nb.y)
                if c < best_cost and self._segment_free(nb.as_tuple(), (nx, ny), obs_list, occupancy_map=occupancy_map):
                    best_parent = nb
                    best_cost   = c

            new_node = Node(nx, ny, parent=best_parent, cost=best_cost)
            nodes.append(new_node)

            # 4. Rewire: reconecta vizinhos se o novo nó é mais barato
            for nb in neighbors:
                c = new_node.cost + math.hypot(nb.x - nx, nb.y - ny)
                if c < nb.cost and self._segment_free((nx, ny), nb.as_tuple(), obs_list, occupancy_map=occupancy_map):
                    nb.parent = new_node
                    nb.cost   = c

            # 5. Atualiza melhor goal
            if new_node.dist_xy(gx, gy) <= self.goal_tolerance:
                if self._segment_free((nx, ny), goal, obs_list, occupancy_map=occupancy_map):
                    g_cost = new_node.cost + math.hypot(nx - gx, ny - gy)
                    if best_goal is None or g_cost < best_goal.cost:
                        best_goal = Node(*goal, parent=new_node, cost=g_cost)

        debug = DebugData(tree_edges=self._build_tree_edges(nodes))

        if best_goal is not None:
            return self._reconstruct_path(best_goal), debug

        return None, debug


# ══════════════════════════════════════════════════════════════
#  PRM
# ══════════════════════════════════════════════════════════════

class PRMPlanner(BasePlanner):
    """
    PRM — Probabilistic Roadmap (Kavraki et al., 1996).

    Fase 1 (construção): amostra n_samples pontos livres e conecta
    cada um aos k_neighbors mais próximos com aresta livre.

    Fase 2 (query): adiciona start e goal ao grafo e busca o
    caminho mais curto com Dijkstra.

    Parâmetros
    ----------
    n_samples    : número de amostras aleatórias
    k_neighbors  : conexões por nó
    """

    def __init__(self, bounds, robot_radius=0.3, seed=None,
                 n_samples=500, k_neighbors=10):
        super().__init__(bounds, robot_radius, seed)
        self.n_samples   = n_samples
        self.k_neighbors = k_neighbors

    def _plan(self, start, goal, obs_list, occupancy_map=None):
        # ── Fase 1: construção do roadmap ──────────────────────
        samples = [Node(*start), Node(*goal)]

        for _ in range(self.n_samples):
            for _ in range(100):          # tenta até achar ponto livre
                x, y = self._random_sample()
                if self._point_free(x, y, obs_list, occupancy_map=occupancy_map):
                    samples.append(Node(x, y))
                    break

        # Grafo como dicionário de adjacências {idx: [(idx_vizinho, custo)]}
        n      = len(samples)
        graph: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(n)}
        edges  = []

        for i, node in enumerate(samples):
            # Ordena todos os outros por distância e pega os k mais próximos
            dists   = sorted(
                [(node.dist(samples[j]), j) for j in range(n) if j != i]
            )
            for _, j in dists[:self.k_neighbors]:
                p1 = node.as_tuple()
                p2 = samples[j].as_tuple()
                if self._segment_free(p1, p2, obs_list, occupancy_map=occupancy_map):
                    cost = node.dist(samples[j])
                    graph[i].append((j, cost))
                    graph[j].append((i, cost))
                    edges.append((*p1, *p2))

        # ── Fase 2: Dijkstra de start (idx=0) a goal (idx=1) ──
        INF  = float("inf")
        dist = [INF] * n
        prev = [-1]  * n
        dist[0] = 0.0
        pq = [(0.0, 0)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            if u == 1:          # chegou ao goal
                break
            for v, w in graph[u]:
                nd = dist[u] + w
                if nd < dist[v]:
                    dist[v] = nd
                    prev[v] = u
                    heapq.heappush(pq, (nd, v))

        debug = DebugData(graph_edges=edges)

        if dist[1] == INF:
            return None, debug

        # Reconstrói caminho
        path_idx, cur = [], 1
        while cur != -1:
            path_idx.append(cur)
            cur = prev[cur]
        path_idx.reverse()
        path = [samples[i].as_tuple() for i in path_idx]

        return path, debug


# ══════════════════════════════════════════════════════════════
#  BIT*
# ══════════════════════════════════════════════════════════════

class BITStarPlanner(BasePlanner):
    """
    BIT* — Batch Informed Trees (Gammell et al., 2015).

    Ideia central: combina a completude assintótica do RRT* com a
    eficiência do A* usando uma elipsoide de busca informada.

    Funcionamento simplificado
    --------------------------
    1. Amostra um batch de pontos dentro da elipsoide definida pelo
       custo da melhor solução conhecida (ou o espaço todo na 1ª iteração).
    2. Expande as arestas em ordem de f = g_T(v) + h(v) (como A*).
    3. Ao encontrar uma solução melhor, encolhe a elipsoide e repete.

    Parâmetros
    ----------
    batch_size   : amostras por iteração
    max_iter     : número máximo de batches
    goal_tolerance: distância para declarar goal atingido (m)
    """

    def __init__(self, bounds, robot_radius=0.3, seed=None,
                 batch_size=200, max_iter=20, goal_tolerance=0.5):
        super().__init__(bounds, robot_radius, seed)
        self.batch_size    = batch_size
        self.max_iter      = max_iter
        self.goal_tolerance = goal_tolerance

    # ── heurística admissível: distância euclidiana ────────────
    @staticmethod
    def _h(node: Node, goal: tuple) -> float:
        return math.hypot(node.x - goal[0], node.y - goal[1])

    # ── amostragem informada dentro da elipsoide ───────────────
    def _informed_sample(
        self,
        start: tuple,
        goal:  tuple,
        c_best: float,
    ) -> tuple[float, float]:
        """
        Amostra uniformemente dentro da elipsoide prolata cuja soma
        das distâncias aos focos (start, goal) é c_best.

        Se c_best = inf, amostra uniformemente no espaço todo.
        """
        c_min = math.hypot(goal[0]-start[0], goal[1]-start[1])

        if c_best == float("inf") or c_best <= c_min:
            return self._random_sample()

        # Centro e eixos da elipsoide
        cx = (start[0] + goal[0]) / 2
        cy = (start[1] + goal[1]) / 2

        a = c_best / 2                       # semi-eixo maior
        b = math.sqrt(max(0, c_best**2 - c_min**2)) / 2   # semi-eixo menor

        # Ângulo de rotação (alinha o eixo maior com start→goal)
        theta = math.atan2(goal[1]-start[1], goal[0]-start[0])

        # Amostra no círculo unitário e transforma
        while True:
            # Amostra no disco unitário
            r   = math.sqrt(self.rng.random())
            ang = self.rng.uniform(0, 2*math.pi)
            ux, uy = r*math.cos(ang), r*math.sin(ang)

            # Escala para a elipsoide
            ex = a * ux
            ey = b * uy

            # Rotaciona e translada
            x = cx + ex*math.cos(theta) - ey*math.sin(theta)
            y = cy + ex*math.sin(theta) + ey*math.cos(theta)

            if self._in_bounds(x, y):
                return x, y

    def _plan(self, start, goal, obs_list, occupancy_map=None):
        gx, gy = goal

        # Árvore T: rooted em start
        root  = Node(*start, cost=0.0)
        V     = [root]           # vértices na árvore
        c_best = float("inf")    # custo da melhor solução
        best_goal_node: Node | None = None
        all_edges = []

        for _batch in range(self.max_iter):

            # 1. Gera batch de amostras informadas
            samples = []
            for _ in range(self.batch_size):
                for _ in range(50):
                    x, y = self._informed_sample(start, goal, c_best)
                    if self._point_free(x, y, obs_list, occupancy_map=occupancy_map):
                        samples.append(Node(x, y))
                        break

            # 2. Para cada amostra, tenta conectar ao melhor vértice
            #    da árvore (como RRT* com escolha de pai por custo)
            for s in samples:
                # Candidatos na árvore ordenados por custo estimado total
                candidates = sorted(
                    V,
                    key=lambda v: v.cost + v.dist(s) + self._h(s, goal)
                )

                for v in candidates:
                    edge_cost = v.dist(s)
                    new_cost  = v.cost + edge_cost

                    # Poda: se o melhor caso possível já é pior que c_best, descarta
                    if new_cost + self._h(s, goal) >= c_best:
                        break

                    if not self._segment_free(v.as_tuple(), s.as_tuple(), obs_list, occupancy_map=occupancy_map):
                        continue

                    s.parent = v
                    s.cost   = new_cost
                    V.append(s)
                    all_edges.append((*v.as_tuple(), *s.as_tuple()))

                    # Rewire vizinhos
                    for nb in V:
                        if nb is s or nb is v:
                            continue
                        rc = s.cost + s.dist(nb)
                        if rc < nb.cost:
                            if self._segment_free(s.as_tuple(), nb.as_tuple(), obs_list, occupancy_map=occupancy_map):
                                nb.parent = s
                                nb.cost   = rc

                    # Verifica goal
                    if s.dist_xy(gx, gy) <= self.goal_tolerance:
                        g_cost = s.cost + s.dist_xy(gx, gy)
                        if g_cost < c_best:
                            c_best = g_cost
                            best_goal_node = Node(*goal, parent=s, cost=g_cost)

                    break   # conectou: passa para próxima amostra

        debug = DebugData(tree_edges=all_edges)

        if best_goal_node is not None:
            return self._reconstruct_path(best_goal_node), debug

        return None, debug
