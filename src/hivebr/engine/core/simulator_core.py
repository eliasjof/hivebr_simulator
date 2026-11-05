"""
simulator_core.py
-----------------
Headless simulation core - pure Python, no pygame dependency.

This is the main entry point for running simulations in Pyodide/WASM
or headless on a server. It provides a clean step(dt, commands) API
that returns serializable state for web frontend rendering.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any
import math
import numpy as np
from copy import deepcopy

from .config import DEFAULT_CONFIG, deepcopy_config
from .world import World
from .robots import create_fleet
from .lidar import Lidar
from .waypoints import WaypointManager
from .track_editor import TrackEditor
from .data_logger import DataLogger
from .interaction import detect_robot_collisions, resolve_robot_overlaps, build_neighbors
from hivebr.state import Command, RobotState
from hivebr.kinematics import normalize_command


@dataclass
class SimStepResult:
    """Resultado de um step de simulação."""
    states: Dict[int, RobotState]           # Estado de todos os robôs
    lidar_readings: List[List[Tuple]]       # LiDAR por robô
    collisions: List[bool]                  # Colisão por robô
    sim_time: float                         # Tempo acumulado
    collision_events: List[dict]            # Novos eventos de colisão


class SimulatorCore:
    """Núcleo de simulação headless - zero dependências de rendering."""
    
    def __init__(self, config: dict):
        """
        Inicializa mundo, frota, LiDAR, waypoints, logger.
        Não cria janela, não inicializa pygame.
        """
        self.config = config
        self.dt = 0.03
        self.sim_time = 0.0
        
        # Componentes core
        self.world = World(config)
        self.robots = create_fleet(config)
        self.num_robots = len(self.robots)
        self.lidar = Lidar(config)
        self.waypoint_managers = [WaypointManager(config) for _ in range(self.num_robots)]
        self.logger = DataLogger()
        
        # Track editor
        self.track_editor = TrackEditor(self.world, config)
        
        # Estado de colisão
        self.collisions = [False] * self.num_robots
        self.collision_events: List[dict] = []
        self._active_collision_keys: set = set()
        self.last_commands = [{} for _ in range(self.num_robots)]
        
        # Simulation state flags
        self.running_simulation = True
        
        # Carrega cena inicial do config
        self._load_scene_from_config()
    
    def step(self, dt: float, commands: Dict[int, Command]) -> SimStepResult:
        """
        Avança um passo de simulação.
        
        Args:
            dt: Delta time (segundos)
            commands: {robot_id: Command} - comandos do controller/agent
            
        Returns:
            SimStepResult com estados, LiDAR, colisões, tempo
        """
        # 1. Atualiza waypoints e LiDAR (snapshot congelado)
        goals = []
        lidar_robots = self._get_lidar_robot_obstacles()
        
        for i, robot in enumerate(self.robots):
            self.waypoint_managers[i].update(robot.position)
            goals.append(self.waypoint_managers[i].get_current_waypoint())
        
        lidar_readings = []
        for i, robot in enumerate(self.robots):
            readings = self.lidar.cast_rays(robot, self.world, lidar_robots)
            lidar_readings.append(readings)
        
        # 2. Aplica ruído gaussiano se habilitado
        noisy_commands = self._apply_noise(commands)
        self.last_commands = commands  # Guarda comando cru para logger
        
        # 3. Integração simultânea (ordem-independente)
        for i, robot in enumerate(self.robots):
            if not self.collisions[i]:
                robot.step(noisy_commands.get(i, {}), dt)
        
        # 4. Detecção de colisões
        self._detect_collisions()
        
        # 5. Logger
        self.logger.draw_callback(self, None)  # screen=None para headless
        
        # 6. Prepara estados de retorno
        states = self._get_states(goals)
        
        self.sim_time += dt
        
        return SimStepResult(
            states=states,
            lidar_readings=lidar_readings,
            collisions=self.collisions.copy(),
            sim_time=self.sim_time,
            collision_events=self._pop_new_collision_events()
        )
    
    def reset(self):
        """Reseta simulação para estado inicial."""
        for robot in self.robots:
            robot.reset()
        for wm in self.waypoint_managers:
            wm.current_index = 0
        if self.track_editor:
            self.track_editor.clear()
        self.collisions = [False] * self.num_robots
        self.sim_time = 0.0
        self.collision_events = []
        self._active_collision_keys = set()
        self.logger.reset()
    
    def set_waypoints(self, robot_id: int, waypoints: List):
        if 0 <= robot_id < self.num_robots:
            self.waypoint_managers[robot_id].waypoints = [list(wp) for wp in waypoints]
            self.waypoint_managers[robot_id].current_index = 0
    
    def add_obstacle(self, x: float, y: float, radius: float):
        self.world.add_obstacle((x, y), radius)
    
    def load_occupancy_map(self, image_bytes: bytes, resolution: float, robot_radius: float):
        """Carrega mapa de ocupação a partir de bytes (para web upload)."""
        from io import BytesIO
        from PIL import Image
        from .occupancy_grid import OccupancyGridMap
        
        img = Image.open(BytesIO(image_bytes)).convert("L")
        grid = np.flipud(np.array(img) < 128)
        grid_map = OccupancyGridMap.from_grid(grid, resolution, robot_radius, self.config["colors"])
        self.world.set_grid_map(grid_map)
        self.config["world"]["map_image"] = "uploaded_map.png"
        self.config["world"]["resolution"] = resolution
    
    def load_line_map(self, image_bytes: bytes, resolution: float):
        """Carrega mapa de linha a partir de bytes."""
        from io import BytesIO
        from PIL import Image
        from .line_map import LineTrackMap
        
        img = Image.open(BytesIO(image_bytes)).convert("L")
        gray = np.array(img, dtype=np.uint8)
        line_map = LineTrackMap.from_gray(gray, resolution, self.config["colors"])
        self.world.set_line_map(line_map)
        self.config["world"]["line_map_image"] = "uploaded_track.png"
        self.config["world"]["resolution"] = resolution
    
    def get_config(self) -> dict:
        return self.config
    
    def export_log(self, format: str = "pkl") -> bytes:
        """Exporta log em memória (pickle/csv)."""
        import io
        buf = io.BytesIO()
        if format == "pkl":
            import pickle
            pickle.dump(self.logger.result(), buf)
        else:
            # CSV export would go here
            pass
        return buf.getvalue()
    
    # --- Métodos internos ---
    
    def _load_scene_from_config(self):
        # -----------------------------
        # Obstáculos
        # -----------------------------
        self.world.obstacles.clear()
        for obs in self.config.get("obstacles", []):
            self.world.add_obstacle((obs["x"], obs["y"]), obs["radius"])

        # -----------------------------
        # Waypoints
        # -----------------------------
        for manager in self.waypoint_managers:
            manager.clear()

        for index, robot_cfg in enumerate(self.config.get("robots", [])):
            if index >= self.num_robots:
                break
            for wp in robot_cfg.get("waypoints", []):
                self.waypoint_managers[index].add_waypoint(wp)

        for wp in self.config.get("waypoints", {}).get("points", []):
            self.waypoint_managers[0].add_waypoint(wp)
    
    def _get_lidar_robot_obstacles(self):
        """Retorna lista de robôs para serem tratados como obstáculos no LiDAR."""
        policies = self.config.get("interaction", {})
        if not bool(policies.get("robot_collision", True)):
            return None
        policy = str(policies.get("collision_policy", "stop")).lower()
        if policy in ("none", "off", "ignore"):
            return None
        if self.num_robots > 1:
            return self.robots
        return None
    
    def _apply_noise(self, commands: Dict[int, Command]) -> Dict[int, Command]:
        """Adiciona ruído gaussiano às velocidades de atuação."""
        cfg = self.config.get("noise", {})
        if not cfg.get("enabled", False):
            return commands

        sigma_v = float(cfg.get("sigma_v", 0.0) or 0.0)
        sigma_w = float(cfg.get("sigma_omega", 0.0) or 0.0)
        if sigma_v <= 0.0 and sigma_w <= 0.0:
            return commands
        limit = cfg.get("limit", 3.0)

        linear_keys = ("v", "vx", "vy", "speed")
        angular_keys = ("omega", "steer")

        noisy_commands = {}
        for robot_id, command in commands.items():
            if not command:
                noisy_commands[robot_id] = command
                continue
            noisy = dict(command)
            if sigma_v > 0.0:
                for key in linear_keys:
                    if key in noisy:
                        noisy[key] = float(noisy[key]) + self._gaussian(sigma_v, limit)
            if sigma_w > 0.0:
                for key in angular_keys:
                    if key in noisy:
                        noisy[key] = float(noisy[key]) + self._gaussian(sigma_w, limit)
            noisy_commands[robot_id] = noisy
        return noisy_commands
    
    @staticmethod
    def _gaussian(sigma: float, limit: float) -> float:
        value = float(np.random.normal(0.0, sigma))
        if limit is not None and float(limit) > 0.0:
            bound = float(limit) * sigma
            value = float(np.clip(value, -bound, bound))
        return value
    
    def _detect_collisions(self):
        policies = self.config.get("interaction", {})
        safety_margin = float(policies.get("robot_safety_margin", 0.0))
        collision_policy = str(policies.get("collision_policy", "stop")).lower()
        evaluate_robot_collision = self._robot_collision_enabled(policies)
        
        current_collision_keys: set = set()
        
        # Colisão estática (por robô)
        for index, robot in enumerate(self.robots):
            if self.collisions[index]:
                continue
            source = self._static_collision_source(robot, index)
            if source is not None:
                key, event = source
                self.collisions[index] = True
                current_collision_keys.add(key)
                self._emit_collision(key, event)
        
        # Interação robô-robô
        if self.num_robots > 1 and evaluate_robot_collision:
            pairs = detect_robot_collisions(self.robots, safety_margin)
            if pairs:
                if collision_policy == "stop":
                    for i, j, _ in pairs:
                        self.collisions[i] = True
                        self.collisions[j] = True
                elif collision_policy == "resolve":
                    resolve_robot_overlaps(
                        self.robots,
                        safety_margin,
                        float(policies.get("resolve_push", 0.05)),
                    )
                for i, j, distance in pairs:
                    key = ("robot", min(i, j), max(i, j))
                    current_collision_keys.add(key)
                    self._emit_collision(
                        key,
                        {
                            "kind": "robot",
                            "robots": [int(i), int(j)],
                            "distance": float(distance),
                        },
                    )
        
        self._active_collision_keys = current_collision_keys
    
    def _robot_collision_enabled(self, policies: dict) -> bool:
        if not bool(policies.get("robot_collision", True)):
            return False
        policy = str(policies.get("collision_policy", "stop")).lower()
        return policy not in ("none", "off", "ignore")
    
    def _static_collision_source(self, robot, index):
        """Detecta colisão estática e devolve ``(chave, evento)`` ou ``None``."""
        q = robot.position
        r_robot = robot.radius

        if self.world.grid_map is not None:
            if self.world.grid_map.is_occupied(q[0], q[1], use_inflated=True):
                return (
                    ("grid", index),
                    {"kind": "grid", "robots": [index]},
                )

        for obs_index, obs in enumerate(self.world.obstacles):
            center = self.world.get_position(obs)
            r_obs = self.world.obstacle_radius(obs)
            dist = float(np.linalg.norm(q - center))
            if dist < (r_obs + r_robot):
                return (
                    ("obstacle", index, obs_index),
                    {
                        "kind": "obstacle",
                        "robots": [index],
                        "obstacle_index": obs_index,
                        "obstacle_xy": [float(center[0]), float(center[1])],
                        "distance": dist,
                    },
                )

        return None
    
    def _emit_collision(self, key, event):
        """Registra o início de uma colisão (borda de subida), com timestamp."""
        if key in self._active_collision_keys:
            return
        record = dict(event)
        record["t"] = float(self.sim_time)
        self.collision_events.append(record)
    
    def _pop_new_collision_events(self) -> List[dict]:
        """Retorna e limpa eventos de colisão recém-registrados."""
        events = self.collision_events.copy()
        self.collision_events.clear()
        return events
    
    def _get_states(self, goals) -> Dict[int, RobotState]:
        states = {}
        for i, robot in enumerate(self.robots):
            st = robot.state()
            goal_tuple = tuple(float(v) for v in goals[i]) if goals[i] is not None else None
            states[i] = RobotState(
                id=i,
                x=float(st.get("x", getattr(robot, "x", 0.0))),
                y=float(st.get("y", getattr(robot, "y", 0.0))),
                theta=float(st.get("theta", getattr(robot, "theta", 0.0))),
                v=float(st.get("v", 0.0)),
                omega=float(st.get("omega", 0.0)),
                type=str(st.get("type", "differential")),
                radius=float(getattr(robot, "radius", 0.1375)),
                battery=float(getattr(robot, "battery_percent", 100.0)),
                goal=goal_tuple,
            )
        return states