from __future__ import annotations
import json
import os
import pygame
import pygame_gui
import numpy as np
import yaml

from hivebr.engine import config
from .data_logger import DataLogger
from .camera import Camera2D
from .world import World
from .robots import create_robot, create_fleet
from .lidar import Lidar
from .waypoints import WaypointManager
from .track_editor import TrackEditor
from .ui.gui import GUI
from . import interaction
import yaml
from copy import deepcopy



# def get_emoji_font(size):
#     candidates = [
#         "Segoe UI Emoji",      # Windows
#         "noto color emoji",    # Linux
#         "segoeui"
#         "Apple Color Emoji",   # macOS
#     ]

#     for name in candidates:
#         try:
#             font = pygame.font.SysFont(name, size)
#             if font:
#                 return font
#         except:
#             pass

#     return pygame.font.Font(None, size)
from pathlib import Path


assets_dir = Path(__file__).parent / "assets"


def _render_honeybee_icon(size: int = 256):
    """Render the honeybee emoji (🐝) into a square surface for the window icon."""
    emoji = "\U0001F41D"

    candidates = [
        Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "seguiemj.ttf",
        Path("/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"),
        Path("/usr/share/fonts/noto/NotoColorEmoji.ttf"),
        Path("/System/Library/Fonts/Apple Color Emoji.ttc"),
    ]
    font_paths = [str(p) for p in candidates if p.exists()]
    for name in ("Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"):
        match = pygame.font.match_font(name)
        if match:
            font_paths.append(match)

    for font_path in font_paths:
        try:
            font = pygame.font.Font(font_path, size)
            glyph = font.render(emoji, True, (255, 255, 255))
        except Exception:
            continue

        if glyph.get_width() == 0 or glyph.get_height() == 0:
            continue
        if int(pygame.surfarray.array_alpha(glyph).max()) == 0:
            continue

        side = max(glyph.get_width(), glyph.get_height())
        icon = pygame.Surface((side, side), pygame.SRCALPHA)
        icon.blit(
            glyph,
            ((side - glyph.get_width()) // 2, (side - glyph.get_height()) // 2),
        )
        return pygame.transform.smoothscale(icon, (size, size))

    return None


# =====================================================================
# CONFIGURAÇÃO PADRÃO (DEFAULT CONFIG)
# =====================================================================
DEFAULT_CONFIG = {
    "window": {
        "width": 1400, "height": 750, "min_width": 1100, "min_height": 650,
        "panel_width": 300, "title": "NavSim2D"
    },
    "world": {
        "width": 20.0, "height": 12.0, "grid_size": 1.0, "obstacle_radius": 0.4,
        "show_origin": True, "show_axes": True, "default_obstacle_radius": 0.4,
        "obstacles": [
            [6.0, 5.0, 1.2],
            [13.163636363636364, 5.709090909090909, 0.4]
        ]
    },
    "camera": {
        "initial_zoom": 1.0, "min_zoom": 0.25, "max_zoom": 8.0,
        "zoom_step": 1.1, "margin_x": 1.0, "margin_y": 1.0
    },
    "robot": {
        "type": "differential",
        "initial_pose": [2.5, 2.5, 0.0],
        "radius": 0.1375, "length": 0.39, "width": 0.275, "wheel_base": 0.285,
        "max_speed": 3.0, "max_omega": 4.0, "max_steer": 0.52,
        "path_max_length": 4000, "tau_v": 0.2
    },
    "lidar": {
        "enabled": False, "num_rays": 101, "range": 12.0, "fov_deg": 360
    },
    "waypoints": {
        "goal_tolerance": 0.5,
        "define_orientation": True,
        "show_tolerance_circle": False,
        "points": []
    },
    "controller": {
        "enabled": True, "attractive_gain": 1.0, "repulsive_gain": 2.0,
        "repulsive_radius": 2.0, "max_repulsive_force": 8.0,
        "force_filter_alpha": 0.35, "command_filter_alpha": 0.4,
        "obstacle_slowdown_distance": 2.0, "min_obstacle_speed_factor": 0.2,
        "min_lidar_distance": 0.08, "linear_gain": 0.6, "angular_gain": 0.6,
        "max_steer_rate": 0.52, "curvature_speed_gain": 2.0,
        "tangential_gain": 1.5, "stagnation_radius": 0.15,
        "local_minima_angle_deg": 90.0, "virtual_subgoal_offset": 2.0,
        "emergency_brake_distance": 0.5, "emergency_safe_distance": 0.65,
        "emergency_rear_clearance": 0.5, "reverse_speed": -0.25,
        "reverse_duration_s": 1.2
    },
    "colors": {
        "background": [30, 30, 30], "grid": [50, 50, 50],
        "panel": [20, 20, 20], "robot": [30, 144, 255],
        "obstacle": [40, 120, 40], "waypoint": [255, 140, 0],
        "goal": [57, 255, 20], "path": [30, 144, 255],
        "lidar": [0, 255, 255], "red": [220, 50, 50],
        "green": [0, 255, 0], "white": [255, 255, 255],
        "black": [0, 0, 0], "silver":[192,192,186],
        "fleet": [
            [30, 144, 255], [220, 20, 60], [50, 205, 50], [255, 165, 0],
            [148, 0, 211], [0, 206, 209], [255, 105, 180], [255, 215, 0]
        ]
    },
    "interaction": {
        "collision_policy": "stop",
        "robot_collision": True,
        "robot_safety_margin": 0.0,
        "resolve_push": 0.05,
        "comm_radius": None,
        "show_robot_links": False
    },
    "noise": {
        "enabled": False,
        "sigma_v": 0.0,
        "sigma_omega": 0.0,
        "limit": 3.0,
        "seed": None
    },
    "obstacles": [],
    "show_times": True,
    "theme": "dark"
}

THEMES = {
    "dark": {
        "background": [30, 30, 30], "grid": [50, 50, 50],
        "panel": [20, 20, 20], "robot": [30, 144, 255],
        "obstacle": [40, 120, 40], "waypoint": [180, 150, 0],
        "goal": [57, 255, 20], "path": [30, 144, 255],
        "lidar": [0, 255, 255], "red": [220, 50, 50],
        "green": [0, 255, 0], "white": [255, 255, 255],
        "black": [0, 0, 0],
        "fleet": [
            [30, 144, 255], [220, 20, 60], [50, 205, 50], [255, 165, 0],
            [148, 0, 211], [0, 206, 209], [255, 105, 180], [255, 215, 0]
        ],
        "occupancy_inflated": [230, 230, 230], "occupancy_raw": [255, 255, 255], 
        # "occupancy_inflated": [50, 129, 75], "occupancy_raw": [40, 120, 40],
        "occupancy_free": [40, 40, 40]
    },
    "light": {
        "background": [240, 240, 240], "grid": [220, 220, 220],
        "panel": [20, 20, 20], "robot": [30, 144, 255],
        "obstacle": [0, 100, 0], "waypoint": [180, 150, 0],
        "goal": [57, 255, 20], "path": [30, 144, 255],
        "lidar": [0, 150, 150], "red": [200, 0, 0],
        "green": [0, 150, 0], "white": [255, 255, 255],
        "black": [0, 0, 0],
        "fleet": [
            [30, 144, 255], [220, 20, 60], [50, 205, 50], [255, 165, 0],
            [148, 0, 211], [0, 206, 209], [255, 105, 180], [255, 215, 0]
        ],
        "occupancy_inflated": [0, 0, 0], "occupancy_raw": [0, 0, 0],
        # "occupancy_inflated": [50, 129, 75], "occupancy_raw": [40, 120, 40],
        "occupancy_free": [230, 230, 230]
    }
}


class Simulator:
    # Definindo config=None na assinatura do método
    def __init__(self, config: dict = None, controller=None, draw_callback=None, type_robot=None, fleet_controller=None):
        # pygame.init()
        pygame.display.init()
        pygame.font.init()
        
        # -----------------------------------------------------------
        # FALLBACK PARA DEFAULT CONFIG
        # -----------------------------------------------------------
        if config is None:
            print("Carregando configuração padrão.")
            self.config = deepcopy(DEFAULT_CONFIG)
            config = self.config
        else:
            self.config = config

        # Aplicar tema
        theme_name = str(self.config.get("theme", "dark"))
        self.apply_theme(theme_name)

        if type_robot is not None:
            self.config["robot"]["type"] = type_robot
            config["robot"]["type"] = type_robot
        w = int(self.config["window"]["width"]); h = int(self.config["window"]["height"])
        self.min_width = int(self.config["window"].get("min_width", 1000))
        self.min_height = int(self.config["window"].get("min_height", 650))
        self.panel_width = int(self.config["window"].get("panel_width", 300))
        self.colors = self.config["colors"]
        self.width, self.height = w, h
        self.world_view_width = max(400, self.width - self.panel_width)
        self.panel_x = self.world_view_width
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption(self.config["window"].get("title", "NavSim"))

        icon = _render_honeybee_icon()
        if icon is not None:
            pygame.display.set_icon(icon)

        self.clock = pygame.time.Clock()
        self.manager = pygame_gui.UIManager((self.width, self.height))
        self.world = World(self.config)
        self.grid_map = self.world.grid_map
        self.explosion_img = pygame.image.load(
            assets_dir / "explosion.png"
        ).convert_alpha()

        self.camera = Camera2D(
            self.world.width,
            self.world.height,
            self.world_view_width,
            self.height,
            **self.config["camera"]
        )

        
        
        self.robots = create_fleet(self.config)
        self.num_robots = len(self.robots)

        self.track_editor = TrackEditor(self.world, self.config)

        self.lidar = Lidar(self.config)

        self.robot_lidar_readings = [[] for _ in range(self.num_robots)]
        self.collisions = [False] * self.num_robots

        # Último comando cru emitido pelo controller (sem ruído), por robô.
        # Usado pelo DataLogger para registrar "comando vs real".
        self.last_commands = [{} for _ in range(self.num_robots)]

        self._setup_noise()

        self.waypoint_managers = [WaypointManager(self.config) for _ in range(self.num_robots)]

        self.selected_robot_index = 0
        self.robot = self.robots[0]
        self.waypoints = self.waypoint_managers[0]

        self.pending_waypoint_position = None
        self.map_file_dialog = None
        self.pending_map_path = None
        self.resolution_window = None
        self.resolution_entry = None

        # CARREGA CENA
        self.load_scene_from_config()

        self.controller = controller
        self.fleet_controller = fleet_controller
        self.gui = GUI(self.screen, self.manager, self._layout())
        self.running = True
        self.running_simulation = False
        self.dt = 0.03
        self.dragging = False
        self.last_mouse_pos = None
        self.pending_obstacle_position = None

        self.draw_callback = draw_callback

        self.logger = DataLogger()
        
        
    def set_themes(self, new_themes: dict):
        """
        Permite definir dinamicamente os temas do simulador.
        """
        global THEMES
        THEMES = new_themes
        # Re-aplica o tema atual para garantir que as cores sejam atualizadas
        current_theme = self.config.get("theme", "dark")
        self.apply_theme(current_theme)

    def apply_theme(self, theme_name):
        self.config["theme"] = theme_name
        self.config["colors"] = THEMES.get(theme_name, THEMES["dark"])
        self.colors = self.config["colors"]

        # Força o grid a redesenhar com as novas cores:
        if hasattr(self, 'world') and self.world.grid_map is not None:
            self.world.grid_map.colors = self.colors
            self.world.grid_map._inflated_surface = None

    def toggle_theme(self):
        new_theme = "light" if self.config.get("theme") == "dark" else "dark"
        self.apply_theme(new_theme)

    @property
    def lidar_readings(self):
        return self.robot_lidar_readings[self.selected_robot_index]

    @property
    def collision(self):
        return self.collisions[self.selected_robot_index]

    def select_robot(self, index: int):
        self.selected_robot_index = int(index) % self.num_robots
        self.robot = self.robots[self.selected_robot_index]
        self.waypoints = self.waypoint_managers[self.selected_robot_index]
        return self.robot

    def set_robot_waypoints(self, robot_index: int, points):
        self.waypoint_managers[robot_index].waypoints = list(points)
        self.waypoint_managers[robot_index].current_index = 0

    def robot_goal(self, robot_index: int):
        return self.waypoint_managers[robot_index].get_current_waypoint()

    

    def load_scene_from_config(self):
        # -----------------------------
        # Obstáculos
        # -----------------------------

        self.world.obstacles.clear()

        for obs in self.config.get("obstacles", []):
            self.world.add_obstacle((obs["x"], obs["y"]), obs["radius"] )

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

    def _layout(self):
        return {"width": self.width, "height": self.height, "panel_width": self.panel_width, "world_view_width": self.world_view_width, "panel_x": self.panel_x, "config": self.config}

    def resize(self, new_width, new_height):
        self.width = max(int(new_width), self.min_width)
        self.height = max(int(new_height), self.min_height)
        self.world_view_width = max(400, self.width - self.panel_width)
        self.panel_x = self.world_view_width
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.manager.set_window_resolution((self.width, self.height))
        self.camera.resize(self.world_view_width, self.height)
        self.gui.rebuild(self._layout())

    def reset(self):
        for robot in self.robots:
            robot.reset()
        for manager in self.waypoint_managers:
            manager.current_index = 0
        self.camera.reset()
        self.collisions = [False] * self.num_robots
        self.robot_lidar_readings = [[] for _ in range(self.num_robots)]

    def set_goal_tolerance(self, tolerance):
        for manager in self.waypoint_managers:
            manager.goal_tolerance = tolerance
        self.config.setdefault("waypoints", {})["goal_tolerance"] = tolerance

    def set_using_orientation(self, define_orientation):
        for manager in self.waypoint_managers:
            manager.define_orientation = define_orientation

    # ======================================================
    # Editor de pista (line follower)
    # ======================================================
    def toggle_track_editor(self):
        if self.track_editor is None:
            return
        self.track_editor.active = not self.track_editor.active
        if self.track_editor.active:
            # Pausa a simulação para facilitar o desenho.
            self.running_simulation = False
        state = "ON" if self.track_editor.active else "OFF"
        print(
            f"[TrackEditor] Draw mode {state}. Arraste com o botao esquerdo; "
            f"clique em 'Apply Track' para o robo seguir a pista."
        )

    def clear_track(self):
        if self.track_editor is not None:
            self.track_editor.clear()
            print("[TrackEditor] Pista limpa.")

    def apply_track(self):
        if self.track_editor is None:
            return
        path = self.config.get("world", {}).get(
            "drawn_line_map_image", "config/line_drawn.png"
        )
        line_map = self.track_editor.apply(path)
        self.config.setdefault("world", {})["line_map_image"] = path

        pose = self.track_editor.start_pose
        if pose is not None:
            x, y, theta = pose
            for robot in self.robots:
                if hasattr(robot, "set_initial_pose"):
                    robot.set_initial_pose(x, y, theta)

        print(
            f"[TrackEditor] Pista aplicada ({line_map.width_m:.2f}x"
            f"{line_map.height_m:.2f} m, res={line_map.resolution}). Salva em '{path}'."
        )
        if pose is not None:
            print(f"[TrackEditor] Robo posicionado em ({x:.2f}, {y:.2f}).")
        else:
            print("[TrackEditor] Dica: desenhe uma linha antes de aplicar.")


    def save_config(self, path="config/default.yaml"):

        cfg = deepcopy(self.config)

        # ---------------------------------
        # Obstáculos
        # ---------------------------------

        cfg["obstacles"] = []

        for obs in self.world.obstacles:

            cfg["obstacles"].append({
                "x": float(obs[0]),
                "y": float(obs[1]),
                "radius": float(obs[2])
            })

        # ---------------------------------
        # Waypoints (per robot)
        # ---------------------------------
        cfg.setdefault("robots", [])
        for index, manager in enumerate(self.waypoint_managers):
            robot_cfg = cfg["robots"][index] if index < len(cfg["robots"]) else {}
            robot_cfg["waypoints"] = [
                [float(v) for v in wp]
                for wp in manager.waypoints
            ]
            if index >= len(cfg["robots"]):
                cfg["robots"].append(robot_cfg)

        cfg.setdefault("waypoints", {})
        cfg["waypoints"]["points"] = [
            [float(v) for v in wp]
            for wp in self.waypoint_managers[0].waypoints
        ]

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                cfg,
                f,
                sort_keys=False,
                allow_unicode=True
            )

        print(f"Config saved to {path}")



    def mouse_inside_world(self, pos):
        x, y = pos
        return 0 <= x < self.world_view_width and 0 <= y < self.height

    
    def handle_button_event(self, event):
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return

        # Botões da janela/modal de raio do obstáculo
        if event.ui_element == self.gui.obstacle_radius_ok:
            self.confirm_obstacle_radius()
            return

        if event.ui_element == self.gui.obstacle_radius_cancel:
            self.pending_obstacle_position = None
            self.gui.close_obstacle_radius_window()
            return

        e = self.gui.elements

        if event.ui_element == e["start"]:
            self.running_simulation = not self.running_simulation

        elif event.ui_element == e["reset"]:
            self.running_simulation = False
            self.reset()

        elif event.ui_element == e["clear_path"]:
            for robot in self.robots:
                robot.clear_path()

        elif event.ui_element == e["clear_waypoints"]:
            for manager in self.waypoint_managers:
                manager.clear()

        elif event.ui_element == e["clear_obstacles"]:
            self.world.clear_obstacles()

        elif event.ui_element == e["draw_track"]:
            self.toggle_track_editor()

        elif event.ui_element == e["apply_track"]:
            self.apply_track()

        elif event.ui_element == e["clear_track"]:
            self.clear_track()

        elif event.ui_element == e["toggle_theme"]:
            self.toggle_theme()

        elif event.ui_element == e["load_map"]:
            self.map_file_dialog = pygame_gui.windows.UIFileDialog(
                rect=pygame.Rect(160, 50, 600, 500),
                manager=self.manager,
                window_title="Load Map",
                allow_existing_files_only=True,
                allowed_suffixes={".png", ".jpg", ".jpeg"}
            )

        elif event.ui_element == e["toggle_lidar"]:
            self.lidar.enabled = not self.lidar.enabled

        elif event.ui_element == e["toggle_noise"]:
            noise = self.config.setdefault("noise", {})
            noise["enabled"] = not noise.get("enabled", False)
            state = "enabled" if noise["enabled"] else "disabled"
            print(f"[Simulator] Gaussian velocity noise {state} "
                  f"(sigma_v={noise.get('sigma_v', 0.0)}, "
                  f"sigma_omega={noise.get('sigma_omega', 0.0)}, "
                  f"limit={noise.get('limit', 3.0)}).")

        elif event.ui_element == e["toggle_times"]:
            show = not self.config.get("show_times", True)
            self.config["show_times"] = show
            state = "ativada" if show else "desativada"
            print(f"[Simulator] Visualizacao de tempos (line follower) {state}.")

        elif event.ui_element == e["save_config"]:
            self.save_config()

        elif event.ui_element == e["center_camera"]:
            self.camera.center_on_origin_with_margin()
        
        elif event.ui_element == e["plot_log"]:
            self.logger.plot()

        elif event.ui_element == e["reset_logger"]:
            self.logger.reset()

        elif event.ui_element == e["export_log"]:
            # self.gui.process_file_dialog_event(event, self.logger)
            
            self.gui.export_log(self.logger)

    def confirm_obstacle_radius(self):
        if self.pending_obstacle_position is None:
            self.gui.close_obstacle_radius_window()
            return

        try:
            radius_text = self.gui.obstacle_radius_entry.get_text()
            radius = float(radius_text)

            if radius <= 0:
                print("Raio inválido. O raio deve ser maior que zero.")
                return

        except ValueError:
            print("Raio inválido. Digite um número, por exemplo: 0.4")
            return

        self.world.add_obstacle(
            self.pending_obstacle_position,
            radius=radius
        )
        self.config["world"]["obstacles"] = np.array(self.world.obstacles).tolist()

        self.pending_obstacle_position = None
        self.gui.close_obstacle_radius_window()
        
    def check_collision(self, robot=None):
        robot = self.robot if robot is None else robot
        q = robot.position
        r_robot = robot.radius   

        if self.world.grid_map is not None:
            # Alterado para False para que a colisão ocorra de forma mais precisa/profunda
            if self.world.grid_map.is_occupied(q[0], q[1], use_inflated=True):
                return True

        for obs in self.world.obstacles:
            center = self.world.get_position(obs)
            r_obs = self.world.obstacle_radius(obs)

            dist = np.linalg.norm(q - center)

            if dist < (r_obs + r_robot):
                return True

        return False

    def confirm_waypoint_orientation(self):

        if self.pending_waypoint_position is None:
            return

        try:
            theta_deg = float(
                self.gui.orientation_entry.get_text()
            )

        except ValueError:
            theta_deg = 0.0

        theta = np.deg2rad(theta_deg)
        list_waypoints = self.pending_waypoint_position.tolist()
        list_waypoints.append(theta)
        self.waypoints.add_waypoint(
            list_waypoints
        )

        self.pending_waypoint_position = None

        if self.gui.orientation_window:
            self.gui.orientation_window.kill()
            self.gui.orientation_window = None
            
    def open_resolution_window(self):
        if self.resolution_window is not None:
            self.resolution_window.kill()

        self.resolution_window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((200, 200), (250, 150)),
            manager=self.manager,
            window_display_title="Resolução (m/pixel)"
        )

        self.resolution_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((20, 20), (200, 30)),
            manager=self.manager,
            container=self.resolution_window
        )
        self.resolution_entry.set_text("0.1")

        self.resolution_ok_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((75, 60), (100, 30)),
            text="OK",
            manager=self.manager,
            container=self.resolution_window
        )

    def cleanup_closed_windows(self):

        if (
            self.gui.obstacle_radius_window is not None
            and not self.gui.obstacle_radius_window.alive()
        ):
            self.gui.obstacle_radius_window = None
            self.pending_obstacle_position = None

        if (
            self.gui.orientation_window is not None
            and not self.gui.orientation_window.alive()
        ):
            self.gui.orientation_window = None
            self.pending_waypoint_position = None
    
    def is_modal_open(self):
        return (
            self.gui.obstacle_radius_window is not None
            or self.gui.orientation_window is not None
        )

    def process_events(self):
        for event in pygame.event.get():

            # ==================================================
            # EVENTOS BÁSICOS DA JANELA
            # ==================================================

            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.VIDEORESIZE:
                self.resize(event.w, event.h)

            elif event.type == pygame.KEYDOWN:
                if pygame.K_1 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_1
                    if index < self.num_robots:
                        self.select_robot(index)

            # ==================================================
            # PRIMEIRO: ENTREGAR EVENTOS PARA A GUI
            # ==================================================
            # Isso garante que botões, caixas de texto e janelas
            # recebam o clique antes do mundo.

            self.manager.process_events(event)
            
            if (event.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED and
                self.map_file_dialog is not None and
                event.ui_element == self.map_file_dialog):
                
                self.pending_map_path = event.text
                self.open_resolution_window()
                
                self.map_file_dialog.kill()
                self.map_file_dialog = None

            if (event.type == pygame_gui.UI_BUTTON_PRESSED and
                self.resolution_window is not None and
                event.ui_element == self.resolution_ok_button):
                
                try:
                    res = float(self.resolution_entry.get_text())
                    self.world.load_map(self.pending_map_path, res)
                    self.grid_map = self.world.grid_map
                    print(f"Mapa carregado: {self.pending_map_path} com res {res}")
                except Exception as e:
                    print(f"Erro ao carregar mapa: {e}")
                
                self.resolution_window.kill()
                self.resolution_window = None
                self.pending_map_path = None

            self.handle_button_event(event)

            self.gui.process_slider_event(
                event,
                self.robots,
                self.world,
                self.lidar,
                self.config
            )

            # ==================================================
            # ENTER NA CAIXA DE RAIO DO OBSTÁCULO
            # ==================================================

            if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:

                if event.ui_element == self.gui.obstacle_radius_entry:
                    self.confirm_obstacle_radius()
                    continue

                elif event.ui_element == self.gui.orientation_entry:
                    self.confirm_waypoint_orientation()
                    continue

            # ==================================================
            # SE MODAL ESTIVER ABERTA, O MUNDO NÃO RECEBE EVENTO
            # ==================================================
            # Isso evita que clicar no OK vire waypoint.

            if self.is_modal_open():
                continue

            # ==================================================
            # SE O MOUSE ESTIVER SOBRE ALGUM ELEMENTO DA GUI,
            # O MUNDO TAMBÉM NÃO RECEBE EVENTO
            # ==================================================

            if self.manager.get_hovering_any_element():
                continue

            # ==================================================
            # MODO DE DESENHO DA PISTA (LINE FOLLOWER)
            # ==================================================
            if (
                self.track_editor is not None
                and self.track_editor.active
                and self.mouse_inside_world(pygame.mouse.get_pos())
            ):
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    pos = self.camera.screen_to_world(*event.pos)
                    self.track_editor.begin(pos[0], pos[1])
                    continue

                if event.type == pygame.MOUSEMOTION and self.track_editor.drawing:
                    pos = self.camera.screen_to_world(*event.pos)
                    self.track_editor.extend(pos[0], pos[1])
                    continue

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.track_editor.end()
                    continue

            # ==================================================
            # EVENTOS DO MUNDO
            # ==================================================

            if event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()

                if self.mouse_inside_world(mouse_pos):
                    self.camera.zoom_at(mouse_pos, event.y)

            elif event.type == pygame.MOUSEBUTTONDOWN:

                # Botão do meio: pan
                if event.button == 2 and self.mouse_inside_world(event.pos):
                    self.dragging = True
                    self.last_mouse_pos = event.pos

                # Botão esquerdo: waypoint
                elif event.button == 1 and self.mouse_inside_world(event.pos):
                    pos = self.camera.screen_to_world(*event.pos)

                    # define_orientation = self.config["waypoints"].get(
                    #     "define_orientation",
                    #     False
                    # )                    

                    if self.waypoints.define_orientation:                        

                        self.pending_waypoint_position = pos

                        self.gui.open_waypoint_orientation_window(
                            default_angle=0.0
                        )

                    else:

                        self.waypoints.add_waypoint(pos)

                # Botão direito: abre janela para raio do obstáculo ou arrasta (com Shift)
                elif event.button == 3 and self.mouse_inside_world(event.pos):
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        self.dragging = True
                        self.last_mouse_pos = event.pos
                    else:
                        self.pending_obstacle_position = self.camera.screen_to_world(
                            *event.pos
                        )

                        self.gui.open_obstacle_radius_window(
                            default_radius=self.world.default_obstacle_radius
                        )

            elif event.type == pygame.MOUSEBUTTONUP:
                self.dragging = False

            elif event.type == pygame.MOUSEMOTION and self.dragging:
                dx = event.pos[0] - self.last_mouse_pos[0]
                dy = event.pos[1] - self.last_mouse_pos[1]

                self.camera.pan_pixels(dx, dy)

                self.last_mouse_pos = event.pos
    
    def _normalize_fleet_commands(self, raw):
        n = self.num_robots
        if raw is None:
            return [{} for _ in range(n)]
        if isinstance(raw, dict):
            return [raw.get(i, {}) or {} for i in range(n)]
        if isinstance(raw, (list, tuple)):
            commands = [cmd or {} for cmd in raw[:n]]
            commands.extend({} for _ in range(n - len(commands)))
            return commands
        raise TypeError(f"Unsupported fleet command container: {type(raw)!r}")

    def _compute_commands(self, goals):
        if self.fleet_controller is not None:
            raw = self.fleet_controller(
                self.robots,
                goals,
                self.config,
                self.dt,
                self.robot_lidar_readings,
            )
            return self._normalize_fleet_commands(raw)

        if self.controller is None:
            return [{} for _ in range(self.num_robots)]

        commands = []
        for index, robot in enumerate(self.robots):
            goal = goals[index]
            try:
                command = self.controller(
                    robot,
                    self.world,
                    goal,
                    self.config,
                    self.dt,
                    self.robot_lidar_readings[index],
                )
            except TypeError:
                command = self.controller(
                    robot,
                    self.world,
                    goal,
                    self.config,
                    self.dt,
                )
            commands.append(command or {})
        return commands

    # ======================================================
    # Ruído gaussiano de velocidades (atuação)
    # ======================================================

    def _setup_noise(self):
        cfg = self.config.setdefault("noise", {})
        # Allow the noise block to be declared under `robot` as well.
        robot_noise = self.config.get("robot", {}).get("noise")
        if isinstance(robot_noise, dict):
            for key, value in robot_noise.items():
                cfg.setdefault(key, value)
        cfg.setdefault("enabled", False)
        cfg.setdefault("sigma_v", 0.0)
        cfg.setdefault("sigma_omega", 0.0)
        cfg.setdefault("limit", 3.0)
        cfg.setdefault("seed", None)
        # `sigma` is a convenience alias applied to both velocities.
        sigma = cfg.get("sigma")
        if sigma is not None:
            if not cfg.get("sigma_v"):
                cfg["sigma_v"] = float(sigma)
            if not cfg.get("sigma_omega"):
                cfg["sigma_omega"] = float(sigma)
        seed = cfg.get("seed")
        if seed is not None:
            np.random.seed(int(seed))

    @staticmethod
    def _gaussian(sigma, limit):
        value = float(np.random.normal(0.0, sigma))
        if limit is not None and float(limit) > 0.0:
            bound = float(limit) * sigma
            value = float(np.clip(value, -bound, bound))
        return value

    def _apply_noise(self, commands):
        """Adiciona ruído gaussiano às velocidades de atuação.

        ``sigma_v``/``sigma_omega`` são os desvios-padrão das velocidades
        linear e angular. O erro é truncado em ``± limit * sigma``.
        """
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

        noisy_commands = []
        for command in commands:
            if not command:
                noisy_commands.append(command)
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
            noisy_commands.append(noisy)
        return noisy_commands

    def update_simulation(self):
        if not self.running_simulation:
            return

        policies = self.config.get("interaction", {})
        safety_margin = float(policies.get("robot_safety_margin", 0.0))
        collision_policy = str(policies.get("collision_policy", "stop"))
        robot_collision = bool(policies.get("robot_collision", True))

        # ======================================================
        # Recarga (por robô)
        # ======================================================
        active = [True] * self.num_robots
        for index, robot in enumerate(self.robots):
            if not getattr(robot, "is_charging", False):
                continue
            for rp in self.world.recharge_places:
                pos_rp = self.world.get_position(rp)
                tolerance = self.waypoint_managers[index].goal_tolerance
                if np.linalg.norm(robot.position - pos_rp) <= tolerance:
                    robot.going_to_recharge = False
                    if hasattr(robot, "update_battery"):
                        robot.update_battery(self.dt, charge_rate=20.0)
                    if robot.battery_percent >= getattr(robot, "working_battery", 90.0):
                        robot.is_charging = False
                    active[index] = False
                    break

        # ======================================================
        # Waypoints e LiDAR (por robô)
        # ======================================================
        goals = []
        for index, robot in enumerate(self.robots):
            self.waypoint_managers[index].update(robot.position)
            goals.append(self.waypoint_managers[index].get_current_waypoint())
            self.robot_lidar_readings[index] = self.lidar.cast_rays(robot, self.world)

        # ======================================================
        # Comandos a partir de um snapshot congelado da frota
        # ======================================================
        commands = self._compute_commands(goals)

        # Guarda o comando cru (sem ruído) para o logger e aplica o ruído
        # gaussiano de atuação antes de integrar a cinemática.
        self.last_commands = commands
        commands = self._apply_noise(commands)

        # ======================================================
        # Integração simultânea (independente de ordem)
        # ======================================================
        for index, robot in enumerate(self.robots):
            if self.collisions[index] or not active[index]:
                continue
            robot.step(commands[index], self.dt)

        # ======================================================
        # Colisão estática (por robô)
        # ======================================================
        for index, robot in enumerate(self.robots):
            if self.collisions[index]:
                continue
            if self.check_collision(robot):
                self.collisions[index] = True

        # ======================================================
        # Interação robô-robô
        # ======================================================
        # ``robot_collision: false`` (ou ``collision_policy: none``) desliga
        # completamente a avaliação de colisão entre os robôs - útil, por
        # exemplo, para várias instâncias de line follower iniciando no mesmo
        # ponto da pista.
        if (
            self.num_robots > 1
            and robot_collision
            and collision_policy not in ("none", "off", "ignore")
        ):
            pairs = interaction.detect_robot_collisions(self.robots, safety_margin)
            if pairs:
                if collision_policy == "stop":
                    for i, j, _ in pairs:
                        self.collisions[i] = True
                        self.collisions[j] = True
                elif collision_policy == "resolve":
                    interaction.resolve_robot_overlaps(
                        self.robots,
                        safety_margin,
                        float(policies.get("resolve_push", 0.05)),
                    )

    def go_to_recharge_place(self, id, angle=0.0, robot_index=None):
        index = self.selected_robot_index if robot_index is None else int(robot_index)
        pos = self.world.get_recharge_place(id)
        robot = self.robots[index]
        robot.going_to_recharge = True
        
        if pos is not None:
            waypoint = [pos[0], pos[1], angle]
            # Adiciona como o objetivo ATUAL (o robô irá para lá agora)
            self.waypoint_managers[index].insert_waypoint_at_current(waypoint)
            # Como inserimos na posição atual, o waypoint que era o atual
            # foi empurrado para a próxima posição. 
            # Não precisamos incrementar o índice.
            print(f"Robô {index} enviado para o ponto de recarga {id}: {waypoint}")
        else:
            print(f"Ponto de recarga {id} não encontrado.")

    def _draw_explosion(self, robot):
        radius_px = max(12, int(3.0 * robot.radius * self.camera.scale))
        explosion = pygame.transform.smoothscale(self.explosion_img, (radius_px, radius_px))
        explosion.set_alpha(180)
        screen_pos = self.camera.world_to_screen(robot.x, robot.y)
        self.screen.blit(
            explosion,
            (screen_pos[0] - radius_px // 2, screen_pos[1] - radius_px // 2),
        )

    def _draw_robot_links(self):
        policies = self.config.get("interaction", {})
        if not policies.get("show_robot_links", False) or self.num_robots < 2:
            return
        comm_radius = policies.get("comm_radius")
        neighbors = interaction.build_neighbors(self.robots, comm_radius)
        color = tuple(self.config["colors"].get("silver", [192, 192, 186]))
        for i, js in neighbors.items():
            for j in js:
                if j <= i:
                    continue
                a, b = self.robots[i].position, self.robots[j].position
                pygame.draw.line(
                    self.screen,
                    color,
                    self.camera.world_to_screen(*a),
                    self.camera.world_to_screen(*b),
                    1,
                )

    def draw(self, fps):
        c = self.config["colors"]
        self.screen.fill(tuple(c["background"]))
        
        # Desenha o mapa do mundo
        if self.grid_map is not None:
            # Desenhamos o mapa (se grid_map existir, ele substitui o grid padrão)
            self.world.draw_grid(self.screen, self.camera)
            self.grid_map.draw(self.screen, self.camera, draw_inflated=False)
            if self.world.show_inflation:
                self.grid_map.draw(self.screen, self.camera, draw_inflated=True)
            
        else:
            self.world.draw_line_map(self.screen, self.camera)
            self.world.draw_grid(self.screen, self.camera)

        if self.track_editor is not None and self.track_editor.active:
            self.track_editor.draw(self.screen, self.camera)
            
        self.world.draw_origin(self.screen, self.camera)
        self.world.draw_axes(self.screen, self.camera)
        pygame.draw.rect(self.screen, tuple(c["panel"]), (self.panel_x, 0, self.panel_width, self.height))
        pygame.draw.line(self.screen, tuple(c["white"]), (self.world_view_width, 0), (self.world_view_width, self.height), 2)

        self._draw_robot_links()

        for index, robot in enumerate(self.robots):
            robot.draw_path(self.screen, self.camera)
        self.world.draw_obstacles(self.screen, self.camera)
        self.world.draw_recharge_places(self.screen, self.camera)
        for manager in self.waypoint_managers:
            manager.draw(self.screen, self.camera)
        for index, robot in enumerate(self.robots):
            self.lidar.draw(self.screen, self.camera, robot, self.world)
        for index, robot in enumerate(self.robots):
            robot.draw(self.screen, self.camera)
            if self.collisions[index]:
                self._draw_explosion(robot)

        self.gui.update_info(
            self.robots,
            self.waypoint_managers,
            self.world,
            fps,
            self.running_simulation,
            self.lidar,
            self.camera,
            selected=self.selected_robot_index,
            collisions=self.collisions,
            config=self.config,
        )
        self.manager.draw_ui(self.screen)

        if self.track_editor is not None and self.track_editor.active:
            self.track_editor.draw_cursor_hint(self.screen)

        
        # ==================================================
        # DESENHO CUSTOMIZADO
        # ==================================================        
        if hasattr(self, "draw_callback") and self.draw_callback is not None:
            self.draw_callback(self, self.screen)

        self.logger.draw_callback(self, self.screen)
        pygame.display.flip()

    def run(self):
        while self.running:
            self.step()

        pygame.quit()

    def step(self):
        time_delta = self.clock.tick(60) / 1000.0
        fps = self.clock.get_fps()

        self.cleanup_closed_windows()

        self.process_events()

        self.manager.update(time_delta)

        self.update_simulation()

        self.draw(fps)

        return time_delta
    
    def get_planning_signature(sim):

        obstacles_sig = tuple(
            (
                round(obs[0], 2),
                round(obs[1], 2),
                round(obs[2], 2),
            )
            for obs in sim.world.obstacles
        )

        waypoints_sig = tuple(
            (
                round(wp[0], 2),
                round(wp[1], 2)
            )
            for wp in sim.waypoints.waypoints
        )

        return (
            obstacles_sig,
            waypoints_sig
        )
    def set_map_from_grid(self, grid, resolution, name="generated_map.png"):
        from .occupancy_grid import OccupancyGridMap
        
        # A classe OccupancyGridMap já realiza a inflação automática no __init__
        # se passarmos o robot_radius.
        grid_map = OccupancyGridMap.from_grid(grid, resolution, robot_radius=self.robot.radius, colors=self.colors)
        
        self.world.set_grid_map(grid_map)
        self.grid_map = self.world.grid_map
        # Atualiza o config para salvar no YAML se o usuário clicar em "Save"
        self.config["world"]["map_image"] = name
        self.config["world"]["resolution"] = resolution
