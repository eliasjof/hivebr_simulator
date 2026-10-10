"""
planner_controller.py
---------------------
Controller universal para hivebr.engine — aceita qualquer subclasse
de BasePlanner e exibe o caminho + estrutura de debug na tela.

Uso
---
    from planners import RRTPlanner, RRTStarPlanner, PRMPlanner, BITStarPlanner
    from planner_controller import PlannerController

    ctrl = PlannerController(
        planner_class=RRTStarPlanner,
        planner_kwargs=dict(step_size=0.5, max_iter=2000, rewire_radius=1.0),
        robot_type="holonomic",
        robot_radius=0.3,
    )

    sim = Simulator(config=config, controller=ctrl.controller,
                    draw_callback=ctrl.draw_callback)
    sim.run()
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pygame

from planners.base_planner import BasePlanner, DebugData, parse_obstacles


class PlannerController:
    """
    Controller hivebr.engine compatível com qualquer BasePlanner.

    Parâmetros
    ----------
    planner_class   : subclasse de BasePlanner (não instância)
    planner_kwargs  : kwargs repassados ao construtor do planner
    robot_type      : "holonomic" | "differential" | "ackermann"
    robot_radius    : raio de inflação (m)
    waypoint_tolerance      : distância para avançar waypoint (m)
    replan_on_new_obstacles : replaneja quando obstáculos mudam
    show_debug      : exibe árvore/grafo do planner
    show_path       : exibe caminho encontrado
    """

    _COLOR_TREE    = ( 80, 160,  80,  55)
    _COLOR_GRAPH   = ( 80, 120, 200,  55)
    _COLOR_PATH    = ( 30, 144, 255)
    _COLOR_WP_DONE = (160, 120, 40)
    _COLOR_WP_NEXT = (255, 140, 0)
    _COLOR_WP_LATER = (255, 165, 0)

    def __init__(
        self,
        planner_class: type,
        planner_kwargs: dict | None = None,
        robot_type: str = "holonomic",
        robot_radius: float = 0.3,
        waypoint_tolerance: float = 0.4,
        replan_on_new_obstacles: bool = True,
        search_bounds: tuple | None = None,
        show_debug: bool = True,
        show_path: bool = True,
    ):
        self.planner_class          = planner_class
        self.planner_kwargs         = planner_kwargs or {}
        self.robot_type             = robot_type
        self.robot_radius           = robot_radius
        self.waypoint_tolerance     = waypoint_tolerance
        self.replan_on_new_obstacles = replan_on_new_obstacles
        self.search_bounds          = search_bounds
        self.show_debug             = show_debug
        self.show_path              = show_path

        self._planner:   BasePlanner | None = None
        self._waypoints: list               = []
        self._wp_idx:    int                = 0
        self._last_goal: tuple | None       = None
        self._last_n_obs: int               = -1
        self._debug:     DebugData          = DebugData()
        self._last_robot_path_len: int      = 0  # detecta clear_path


    def reset(self):
        """Limpa o caminho e a estrutura de debug do planner."""
        self._waypoints  = []
        self._wp_idx     = 0
        self._last_goal  = None
        self._last_n_obs = -1
        self._debug      = DebugData()

    # ── stop ──────────────────────────────────────────────────

    def _stop(self) -> dict:
        if self.robot_type == "holonomic":
            return {"vx": 0.0, "vy": 0.0}
        if self.robot_type == "differential":
            return {"v": 0.0, "omega": 0.0}
        return {"speed": 0.0, "steer": 0.0}

    # ── comandos locais ────────────────────────────────────────

    def _cmd(self, robot, tx, ty) -> dict:
        if self.robot_type == "holonomic":
            return self._holonomic(robot, tx, ty)
        if self.robot_type == "differential":
            return self._differential(robot, tx, ty)
        return self._ackermann(robot, tx, ty)

    @staticmethod
    def _holonomic(robot, tx, ty) -> dict:
        dx, dy = tx - robot.x, ty - robot.y
        dist   = math.hypot(dx, dy) + 1e-9
        speed  = min(robot.max_speed, dist * 2.0)
        return {"vx": speed * dx / dist, "vy": speed * dy / dist}

    @staticmethod
    def _differential(robot, tx, ty) -> dict:
        from hivebr.engine.geometry import wrap_to_pi
        dx, dy    = tx - robot.x, ty - robot.y
        dist      = math.hypot(dx, dy) + 1e-9
        angle_err = wrap_to_pi(math.atan2(dy, dx) - robot.theta)
        error_max = 2.0  # distância a partir da qual o ganho é máximo
        kp = robot.max_speed / error_max
        # v     = robot.max_speed * max(0.0, 1.0 - abs(angle_err) * 1.5) if dist > 0.1 else 0.0
        # v = kp*( dx*math.cos(robot.theta) + dy*math.sin(robot.theta) )
        v = robot.max_speed* max(0.0, 1.0 - abs(angle_err) * 1.5) if dist > 0.1 else 0.0
        # omega = math.copysign(min(robot.max_omega, abs(angle_err) * 3.0), angle_err)
        ktheta = robot.max_omega / math.pi
        omega = ktheta * angle_err
        return {"v": v, "omega": omega}

    @staticmethod
    def _ackermann(robot, tx, ty) -> dict:
        from hivebr.engine.geometry import wrap_to_pi, clamp
        dx, dy    = tx - robot.x, ty - robot.y
        angle_err = wrap_to_pi(math.atan2(dy, dx) - robot.theta)
        speed     = robot.max_speed * max(0.2, 1.0 - abs(angle_err))
        steer     = clamp(angle_err, -robot.max_steer, robot.max_steer)
        return {"speed": speed, "steer": steer}

    # ── controller principal ───────────────────────────────────

    def controller(self, robot, world, goal, config, dt, lidar_readings=None) -> dict:
        if goal is None:
            return self._stop()

        # 1. Extrai o theta do objetivo (se existir na configuração YAML)
        goal_theta = float(goal[2]) if len(goal) >= 3 else 0.0
        goal_pos   = (float(goal[0]), float(goal[1]), goal_theta)

        # 2. Extrai o theta real do robô no simulador (se for diferencial/tiver rotação)
        robot_theta = float(robot.theta) if hasattr(robot, 'theta') else 0.0
        robot_pos   = (float(robot.x), float(robot.y), robot_theta)

        bounds    = self.search_bounds if self.search_bounds is not None else (0.0, float(world.width), 0.0, float(world.height))
        n_obs     = len(world.obstacles)

        # Verificação de mudança com tolerância para evitar replanejamento infinito por erro numérico
        epsilon = 0.01 
        goal_changed = False
        if self._last_goal is None:
            goal_changed = True
        else:
            goal_changed = (math.hypot(goal_pos[0]-self._last_goal[0], goal_pos[1]-self._last_goal[1]) > epsilon)
            
        obstacles_changed = (self.replan_on_new_obstacles and n_obs != self._last_n_obs)
        needs_replan = goal_changed or obstacles_changed

        if needs_replan:
            # Instancia (ou reinstancia) o planner com os bounds atuais
            self._planner = self.planner_class(
                bounds=bounds,
                robot_radius=self.robot_radius,
                **self.planner_kwargs,
            )

            name = self.planner_class.__name__
            print(f"[{name}] Planejando...")

            # 3. Agora envia a tupla completa (x, y, theta) para o planner!
            path, debug = self._planner.plan(
                robot_pos, goal_pos, world.obstacles,
                occupancy_map=getattr(world, 'grid_map', None)
            )

            self._waypoints  = path if path else []
            self._debug      = debug
            self._wp_idx     = 0
            self._last_goal  = goal_pos
            self._last_n_obs = n_obs

            if path:
                print(f"[{name}] {len(path)} waypoints.")
            else:
                print(f"[{name}] Caminho não encontrado.")

        # Avança waypoint atual
        while self._wp_idx < len(self._waypoints):
            # Pega apenas os dois primeiros elementos (x, y), ignorando o theta se ele existir
            wx, wy = self._waypoints[self._wp_idx][:2]
            if math.hypot(robot.x - wx, robot.y - wy) < self.waypoint_tolerance:
                self._wp_idx += 1
            else:
                break

        idx       = self._wp_idx
        subtarget = (
            self._waypoints[idx]
            if self._waypoints and idx < len(self._waypoints)
            else goal_pos
        )
        return self._cmd(robot, *subtarget[:2])

    # ── draw_callback ──────────────────────────────────────────

    def draw_callback(self, sim, screen) -> None:
        camera = sim.camera

        # Detecta clear_path: robot.path voltou a 0 ou 1 pontos
        # enquanto antes tinha mais — significa que o botão foi pressionado.
        current_len = len(sim.robot.path)
        if self._last_robot_path_len > 1 and current_len <= 1:
            self.reset()
        self._last_robot_path_len = current_len

        # ── estrutura do planner (árvore ou grafo) ─────────────
        if self.show_debug:
            edges = self._debug.tree_edges or self._debug.graph_edges
            color = self._COLOR_TREE if self._debug.tree_edges else self._COLOR_GRAPH

            if edges:
                surf = pygame.Surface(
                    (camera.viewport_width, camera.viewport_height),
                    pygame.SRCALPHA,
                )
                for x1, y1, x2, y2 in edges:
                    pygame.draw.line(
                        surf, color,
                        camera.world_to_screen(x1, y1),
                        camera.world_to_screen(x2, y2),
                        1,
                    )
                screen.blit(surf, (0, 0))

        # ── caminho encontrado ─────────────────────────────────
        if self.show_path and self._waypoints:
            pts = [camera.world_to_screen(*wp[:2]) for wp in self._waypoints]

            if len(pts) >= 2:
                # Desenha linha pontilhada
                dash_length = 5
                for i in range(len(pts) - 1):
                    p1, p2 = pts[i], pts[i+1]
                    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                    dist = math.hypot(dx, dy)
                    if dist > 0:
                        dashes = int(dist / dash_length)
                        for j in range(dashes):
                            if j % 2 == 0:
                                start = (p1[0] + dx * j / dashes, p1[1] + dy * j / dashes)
                                end = (p1[0] + dx * (j+1) / dashes, p1[1] + dy * (j+1) / dashes)
                                pygame.draw.line(screen, self._COLOR_PATH, start, end, 2)
            
            for i, pt in enumerate(pts):
                if i < self._wp_idx:
                    color = self._COLOR_WP_DONE
                elif i == self._wp_idx:
                    color = self._COLOR_WP_NEXT
                else:
                    color = self._COLOR_WP_LATER
                
                radius = 7 if i == self._wp_idx else 4
                pygame.draw.circle(screen, color, pt, radius)
                pygame.draw.circle(screen, (255, 255, 255), pt, radius, 1)
