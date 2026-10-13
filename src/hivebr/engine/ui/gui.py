from __future__ import annotations
import math
import pygame
import pygame_gui
from hivebr.engine.geometry import distance_between
from hivebr.engine.data_logger import DataLogger
from tkinter import Tk, filedialog
from pathlib import Path

class GUI:
    def __init__(self, screen, manager, layout):
        self.manager = manager
        self.screen = screen
        self.layout = layout
        self.elements = {}
        self.buttons_bottom_y = 0
        self.create_buttons()
        self.create_sliders()
        self.orientation_window = None
        self.orientation_entry = None
        # self.create_info_labels()
        self.export_dialog = None
        self.obstacle_radius_window = None
        self.obstacle_radius_entry = None
        self.obstacle_radius_ok = None
        self.obstacle_radius_cancel = None
        self.font = pygame.font.SysFont(
            "consolas",
            18
        )

    @property
    def panel_x(self):
        return self.layout["panel_x"]

    @property
    def height(self):
        return self.layout["height"]

    def rebuild(self, layout):
        self.layout = layout
        for element in self.elements.values():
            element.kill()
        self.elements.clear()
        self.create_buttons()
        self.create_sliders()
        self.create_info_labels()

    def create_buttons(self):
        x = self.panel_x + 35
        y = 12
        w, h, gap = 230, 30, 32
        
        buttons = [
            ("start", "Start / Pause"),
            ("reset", "Reset"),
            ("clear_path", "Clear Path"),
            ("clear_waypoints", "Clear Waypoints"),
            ("clear_obstacles", "Clear Obstacles"),            
            ("load_map", "Load Map"),
            ("toggle_lidar", "Toggle LiDAR"),
            ("toggle_noise", "Toggle Noise"),
            ("toggle_theme", "Toggle Theme"),
            ("save_config", "Save Config"),
            ("center_camera", "Center Camera"),
            ("plot_log", "Plot Log"),
            ("export_log", "Export Log"),
            ("reset_logger", "Reset Logger")
        ]

        for i, (key, text) in enumerate(buttons):
            self.elements[key] = pygame_gui.elements.UIButton(pygame.Rect(x, y + i*gap, w, h), text, self.manager)
        self.buttons_bottom_y = y + len(buttons) * gap

    def draw_hud(self,        running,        robot,        rtype,        motion,        waypoints,        dist,        fps,        world,        camera    ):
        text = (
            f"{'RUN' if running else 'PAUSE'}"
            f" | {rtype}"
            f" | x={robot.x:.2f}"
            f", y={robot.y:.2f}"
            f" | θ={math.degrees(robot.theta):.1f}°"
            f" | {motion}"
            f" | WP={waypoints.status_text()}"
            f" | d={dist}"
            f" | FPS={fps:.0f}"
            f" | Obs={len(world.obstacles)}"
            f" | Zoom={camera.zoom:.2f}"
        )

        padding = 8

        info_surface = self.font.render(
            text,
            True,
            (255,255,255)
        )

        bg_rect = pygame.Rect(
            5,
            5,
            info_surface.get_width() + 2*padding,
            info_surface.get_height() + 2*padding
        )

        overlay = pygame.Surface(
            (bg_rect.width, bg_rect.height),
            pygame.SRCALPHA
        )

        overlay.fill((0,0,0,180))

        self.screen.blit(
            overlay,
            (bg_rect.x, bg_rect.y)
        )

        self.screen.blit(
            info_surface,
            (10, 10)
        )

    def add_slider(self, key, label, y, start, value_range):
        x = self.panel_x + 35
        w = 230
        self.elements[f"{key}_label"] = pygame_gui.elements.UILabel(pygame.Rect(x, y, 170, 22), label, self.manager)
        self.elements[f"{key}_value"] = pygame_gui.elements.UILabel(pygame.Rect(x+170, y, 60, 22), f"{start:.2f}", self.manager)
        self.elements[key] = pygame_gui.elements.UIHorizontalSlider(pygame.Rect(x, y+22, w, 18), start, value_range, self.manager)

    def create_sliders(self):
        cfg = self.layout["config"]
        start_y = self.buttons_bottom_y + 2
        spacing = 44
        self.add_slider("max_speed", "Max Speed", start_y, cfg["robot"].get("max_speed", 2.0), (0.2, 8.0))
        self.add_slider("max_omega", "Max Omega", start_y + spacing, cfg["robot"].get("max_omega", 2.0), (0.1, 6.0))
        self.add_slider("max_steer", "Max Steering", start_y + 2*spacing, cfg["robot"].get("max_steer", 0.6), (0.1, 1.2))
        self.add_slider("grid_size", "Grid Size", start_y + 3*spacing, cfg["world"].get("grid_size", 1.0), (0.1, 5.0))
        self.add_slider("noise_sigma", "Noise Sigma", start_y + 4*spacing, cfg.get("noise", {}).get("sigma_v", 0.0), (0.0, 1.0))

    def create_info_labels(self):
        x = self.panel_x + 20
        w, h = 260, 30
        y = self.height - 45
        # self.elements["info"] = pygame_gui.elements.UILabel(pygame.Rect(x, y, w, h), "Ready", self.manager)

    def process_slider_event(self, event, robots, world, lidar, config):
        if event.type != pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            return
        e = self.elements
        if event.ui_element == e["max_speed"]:
            value = e["max_speed"].get_current_value(); config["robot"]["max_speed"] = value; e["max_speed_value"].set_text(f"{value:.2f}")
            for robot in robots:
                if hasattr(robot, "max_speed"):
                    robot.max_speed = value
        elif event.ui_element == e["max_omega"]:
            value = e["max_omega"].get_current_value(); config["robot"]["max_omega"] = value; e["max_omega_value"].set_text(f"{value:.2f}")
            for robot in robots:
                if hasattr(robot, "max_omega"):
                    robot.max_omega = value
        elif event.ui_element == e["max_steer"]:
            value = e["max_steer"].get_current_value(); config["robot"]["max_steer"] = value; e["max_steer_value"].set_text(f"{value:.2f}")
            for robot in robots:
                if hasattr(robot, "max_steer"):
                    robot.max_steer = value
        elif event.ui_element == e["grid_size"]:
            world.grid_size = e["grid_size"].get_current_value(); config["world"]["grid_size"] = world.grid_size; e["grid_size_value"].set_text(f"{world.grid_size:.2f}")
        elif event.ui_element == e["noise_sigma"]:
            value = e["noise_sigma"].get_current_value()
            noise = config.setdefault("noise", {})
            noise["sigma_v"] = value
            noise["sigma_omega"] = value
            noise.setdefault("limit", 1.0)
            # Moving the slider enables the noise; setting it to 0 disables it.
            noise["enabled"] = value > 0.0
            e["noise_sigma_value"].set_text(f"{value:.3f}")

    def close_obstacle_radius_window(self):
        if self.obstacle_radius_window is not None:
            self.obstacle_radius_window.kill()

        self.obstacle_radius_window = None
        self.obstacle_radius_entry = None
        self.obstacle_radius_ok = None
        self.obstacle_radius_cancel = None
    
    def open_waypoint_orientation_window(self,default_angle=0.0):

        if self.orientation_window:
            self.orientation_window.kill()

        self.orientation_window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((200, 200), (260, 120)),
            manager=self.manager,
            window_display_title="Waypoint Orientation"
        )

        self.orientation_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((20, 20), (200, 30)),
            manager=self.manager,
            container=self.orientation_window
        )

        self.orientation_entry.set_text(str(default_angle))
        
    def open_obstacle_radius_window(self, default_radius=0.4):
        # Se já existir uma janela aberta, fecha antes
        if self.obstacle_radius_window is not None:
            self.obstacle_radius_window.kill()

        window_rect = pygame.Rect(
            self.panel_x - 360,
            120,
            320,
            180
        )

        self.obstacle_radius_window = pygame_gui.elements.UIWindow(
            rect=window_rect,
            manager=self.manager,
            window_display_title="Novo Obstáculo"
        )

        pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect(20, 35, 260, 30),
            text="Raio do obstáculo:",
            manager=self.manager,
            container=self.obstacle_radius_window
        )

        self.obstacle_radius_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect(20, 70, 260, 32),
            manager=self.manager,
            container=self.obstacle_radius_window
        )

        self.obstacle_radius_entry.set_text(f"{default_radius:.2f}")

        self.obstacle_radius_ok = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(35, 115, 100, 35),
            text="OK",
            manager=self.manager,
            container=self.obstacle_radius_window
        )

        self.obstacle_radius_cancel = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect(165, 115, 100, 35),
            text="Cancelar",
            manager=self.manager,
            container=self.obstacle_radius_window
        )

    def reset_logger(self, logger: DataLogger):
        logger.reset()

    def plot_log(self, logger: DataLogger):
        logger.plot()
    
    

    def export_log(self, logger: DataLogger):

        logs_dir = Path("./logs").resolve()
        logs_dir.mkdir(exist_ok=True)

        root = Tk()
        root.withdraw()

        filename = filedialog.asksaveasfilename(
            title="Salvar Log",
            initialdir=str(logs_dir),
            initialfile="run.pkl",
            defaultextension=".pkl",
            filetypes=[
                ("Pickle files", "*.pkl"),
                ("CSV files", "*.csv"),
                ("Todos os arquivos", "*.*")
            ]
        )

        root.destroy()

        if filename:
            logger.export(filename)
    
    # def export_log(self, logger: DataLogger):
    #     if self.export_dialog is not None:
    #         self.export_dialog.kill()

    #     self.export_dialog = pygame_gui.windows.UIFileDialog(
    #         rect=pygame.Rect(160, 50, 600, 500),
    #         manager=self.manager,
    #         window_title="Export Log",
    #         initial_file_path="./logs/",
    #         allow_existing_files_only=False
    #     )
    # def process_file_dialog_event(self, event, logger: DataLogger):
    #     if (
    #         event.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED
    #         and event.ui_element == self.export_dialog
    #     ):
    #         filename = event.text

    #         if not filename.endswith(".pkl"):
    #             filename += ".pkl"

    #         logger.save(filename)

    #         self.export_dialog = None
    @staticmethod
    def _robot_color(robot):
        return tuple(getattr(robot, "colors", {}).get("robot", (255, 255, 255)))

    def update_info(self, robots, waypoint_managers, world, fps, running, lidar, camera, selected=0, collisions=None, config=None):
        collisions = collisions if collisions is not None else [False] * len(robots)
        selected = selected % max(len(robots), 1)
        robot = robots[selected]
        waypoints = waypoint_managers[selected]

        goal = waypoints.get_current_waypoint()
        dist = "None" if goal is None else f"{distance_between(robot.position, goal[:2]):.2f}"
        state = robot.state()
        rtype = state.get("type", "robot")
        if rtype == "holonomic":
            motion = f"vx={state.get('vx', 0.0):.2f} | vy={state.get('vy', 0.0):.2f}"
        elif rtype == "differential" or rtype == "differential_firstorder":
            motion = f"v={state.get('v', 0.0):.2f} | ω={state.get('omega', 0.0):.2f}"
        elif rtype == "ackermann":
            motion = f"v={state.get('speed', 0.0):.2f} | δ={math.degrees(state.get('steer', 0.0)):.1f}°"
        else:
            motion = "motion=None"

        if config is None:
            config = getattr(robot, "config", {})
        noise = config.get("noise", {})
        noise_on = bool(noise.get("enabled", False))
        noise_text = (
            f"  [NOISE ON  sigma={noise.get('sigma_v', 0.0):.3f}]"
            if noise_on else ""
        )

        rows = [(
            f"{'RUN' if running else 'PAUSE'} | fleet={len(robots)} | selected=B-Bot{selected} "
            f"| FPS={fps:.0f} | Obs={len(world.obstacles)} | Zoom={camera.zoom:.2f}"
            f"{noise_text}",
            (255, 165, 0) if noise_on else (255, 255, 255),
        )]
        rows.append((
            f"B-Bot{selected} ({rtype}) x={robot.x:.2f}, y={robot.y:.2f} θ={math.degrees(robot.theta):.1f}° "
            f"| {motion} | WP={waypoints.status_text()} | d={dist}"
            + ("  [COLLISION]" if collisions[selected] else ""),
            self._robot_color(robot),
        ))
        for index, other in enumerate(robots):
            if index == selected:
                continue
            rows.append((
                f"{'*' if collisions[index] else ' '} B-Bot{index} x={other.x:.2f}, y={other.y:.2f} "
                f"θ={math.degrees(other.theta):.1f}° WP={waypoint_managers[index].status_text()}",
                self._robot_color(other),
            ))

        padding = 8
        line_height = self.font.get_linesize()
        max_width = max(self.font.size(row[0])[0] for row in rows)
        bg_rect = pygame.Rect(5, 5, max_width + 2 * padding, line_height * len(rows) + 2 * padding)

        overlay = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (bg_rect.x, bg_rect.y))

        for row, (text, color) in enumerate(rows):
            surface = self.font.render(text, True, color)
            self.screen.blit(surface, (5 + padding, 5 + padding + row * line_height))

        # --- Assinatura do Desenvolvedor (Canto Inferior Direito) ---
        credit_text = "Developed by Elias J R Freitas"
        
        # 1. Cria uma fonte nova e menor (tamanho 16, por exemplo)
        # O 'None' usa a fonte padrão do Pygame.
        assinatura_font = pygame.font.Font(None, 14) 
        
        # 2. Usa essa NOVA fonte para renderizar o texto
        credit_surface = assinatura_font.render(
            credit_text,
            True,
            (200, 200, 200) 
        )
        
        screen_w, screen_h = self.screen.get_size()
        margin = 5

        # Calcula a posição X e Y para ancorar no canto inferior direito
        credit_x = screen_w - credit_surface.get_width() - margin
        credit_y = screen_h - credit_surface.get_height() - margin

        # Criação do fundo translúcido para a assinatura (mesmo estilo do info)
        credit_bg_rect = pygame.Rect(
            credit_x - padding,
            credit_y - padding,
            credit_surface.get_width() + 2 * padding,
            credit_surface.get_height() + 2 * padding
        )

        credit_overlay = pygame.Surface(
            (credit_bg_rect.width, credit_bg_rect.height),
            pygame.SRCALPHA
        )
        credit_overlay.fill((0, 0, 0, 150)) # Fundo ligeiramente mais transparente (150 de alpha)

        # Desenha o fundo e depois o texto
        self.screen.blit(credit_overlay, (credit_bg_rect.x, credit_bg_rect.y))
        self.screen.blit(credit_surface, (credit_x, credit_y))
