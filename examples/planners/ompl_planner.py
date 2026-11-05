from ompl import base as ob
from ompl import geometric as og
import math
from examples.planners.base_planner import DebugData


class ValidityChecker(ob.StateValidityChecker):

    def __init__(self, si, obstacles, robot_radius, occupancy_map=None, use_se2: bool = False):
        super().__init__(si)
        self.obstacles    = obstacles
        self.robot_radius = robot_radius
        self.use_se2      = use_se2
        self.occupancy_map = occupancy_map

    def isValid(self, state):
        # 1. Trata a estrutura do estado dependendo do espaço escolhido
        if self.use_se2:
            x, y = state.getX(), state.getY()
        else:
            x, y = state[0], state[1]

        # Verifica mapa de ocupação (se existir)
        if self.occupancy_map and self.occupancy_map.is_occupied(x, y, use_inflated=True):
            return False

        for obs in self.obstacles:
            ox, oy = (obs.x, obs.y) if hasattr(obs, "x") else (obs[0], obs[1])
            r      = obs.radius     if hasattr(obs, "radius") else obs[2]
            if math.hypot(x - ox, y - oy) <= r + self.robot_radius:
                return False
        return True


class OMPLPlanner:

    def __init__(
        self,
        bounds,
        planner_type: str = "RRTstar",
        robot_radius: float = 0.3,
        solve_time: float = 1.0,
        use_se2: bool = False,  # <-- Nova flag de configuração
    ):
        self.bounds       = bounds
        self.robot_radius = robot_radius
        self.solve_time   = solve_time
        self.planner_type = planner_type
        self.use_se2      = use_se2

    # ── configuração do espaço ────────────────────────────────

    def _make_si(self, obstacles, occupancy_map=None):
        xmin, xmax, ymin, ymax = self.bounds

        if self.use_se2:
            # Voltamos ao SE2 puro, já que os modelos não-holonômicos não foram compilados
            space = ob.SE2StateSpace()
            
            b = ob.RealVectorBounds(2)
            b.setLow(0, xmin);  b.setHigh(0, xmax)
            b.setLow(1, ymin);  b.setHigh(1, ymax)
            space.setBounds(b)
        else:
            space = ob.RealVectorStateSpace(2)
            b = ob.RealVectorBounds(2)
            b.setLow(0, xmin);  b.setHigh(0, xmax)
            b.setLow(1, ymin);  b.setHigh(1, ymax)
            space.setBounds(b)

        
        si = ob.SpaceInformation(space)
        si.setStateValidityChecker(
            ValidityChecker(si, obstacles, self.robot_radius, occupancy_map=occupancy_map, use_se2=self.use_se2)
        )
        si.setup()
        return si, space


    # ── instancia o planner pelo nome ────────────────────────

    def _make_planner(self, si):
        if not hasattr(og, self.planner_type):
            raise ValueError(
                f"Planner '{self.planner_type}' desconhecido ou indisponível."
            )
        planner_class = getattr(og, self.planner_type)
        return planner_class(si)

    # ── extrai arestas da árvore via PlannerData ──────────────

    def _extract_tree_edges(self, planner, si) -> list[tuple]:
        pd = ob.PlannerData(si)
        planner.getPlannerData(pd)

        edges = []
        n     = pd.numVertices()

        for i in range(n):
            neighbors = pd.getEdges(i)

            v_from = pd.getVertex(i).getState()
            
            # 3. Extração correta da raiz da aresta
            if self.use_se2:
                x1, y1 = v_from.getX(), v_from.getY()
            else:
                x1, y1 = float(v_from[0]), float(v_from[1])

            for j in neighbors:
                v_to = pd.getVertex(j).getState()
                
                # Extração correta do destino da aresta
                if self.use_se2:
                    x2, y2 = v_to.getX(), v_to.getY()
                else:
                    x2, y2 = float(v_to[0]), float(v_to[1])
                    
                edges.append((x1, y1, x2, y2))

        return edges

    # ── plan ─────────────────────────────────────────────────

    def plan(self, start, goal, obstacles, occupancy_map=None) -> tuple[list | None, DebugData]:
        si, space = self._make_si(obstacles, occupancy_map=occupancy_map)

        ss = space.allocState()
        gs = space.allocState()

        # 4. Atribuição das condições de contorno de acordo com o espaço
        if self.use_se2:
            st_theta = float(start[2]) if len(start) >= 3 else 0.0
            gl_theta = float(goal[2])  if len(goal)  >= 3 else 0.0
            
            ss.setX(float(start[0]))
            ss.setY(float(start[1]))
            ss.setYaw(st_theta)

            gs.setX(float(goal[0]))
            gs.setY(float(goal[1]))
            gs.setYaw(gl_theta)
            print(f"Configuração SE(2) - Start: ({ss.getX():.2f}, {ss.getY():.2f}, {ss.getYaw():.2f} rad), "
                  f"Goal: ({gs.getX():.2f}, {gs.getY():.2f}, {gs.getYaw():.2f} rad)")
        else:
            # Espaço R2 tradicional
            ss[0], ss[1] = float(start[0]), float(start[1])
            gs[0], gs[1] = float(goal[0]), float(goal[1])

        pdef = ob.ProblemDefinition(si)
        pdef.setStartAndGoalStates(ss, gs)
        pdef.setOptimizationObjective(ob.PathLengthOptimizationObjective(si))

        planner = self._make_planner(si)
        planner.setProblemDefinition(pdef)
        planner.setup()

        solved = planner.solve(self.solve_time)

        tree_edges = self._extract_tree_edges(planner, si)
        debug      = DebugData(tree_edges=tree_edges)

        if not solved:
            return None, debug

        path = pdef.getSolutionPath()
        path.interpolate()

        # 5. Retorna tuplas com ou sem orientação baseando-se na flag
        if self.use_se2:
            pts = [(s.getX(), s.getY(), s.getYaw()) for s in path.getStates()]
        else:
            pts = [(float(s[0]), float(s[1])) for s in path.getStates()]

        return pts, debug

# ──────────────────────────────────────────────────────────────
# Wrapper Adaptado
# ──────────────────────────────────────────────────────────────

from examples.planners.base_planner import BasePlanner

class OMPLPlannerAdapter(BasePlanner):

    def __init__(
        self,
        bounds,
        robot_radius: float = 0.3,
        seed=None,
        planner_type: str = "RRTstar",
        solve_time: float = 1.0,
        use_se2: bool = False,  # <-- Passado pelo Controller
    ):
        super().__init__(bounds, robot_radius, seed)
        self._ompl = OMPLPlanner(
            bounds=bounds,
            planner_type=planner_type,
            robot_radius=robot_radius,
            solve_time=solve_time,
            use_se2=use_se2,
        )

    def _plan(self, start, goal, obs_list, occupancy_map=None):
        return self._ompl.plan(start, goal, obs_list, occupancy_map=occupancy_map) 
