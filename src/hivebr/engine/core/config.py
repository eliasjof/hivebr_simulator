from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml
from copy import deepcopy


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
        "define_orientation": False,
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
    "theme": "dark",
    "running_simulation": False,
    "gui": {
        "buttons": [
            "start", "reset", "clear_path", "clear_waypoints", "clear_obstacles",
            "load_map", "draw_track", "apply_track", "clear_track",
            "toggle_lidar", "toggle_noise", "toggle_times", "toggle_theme",
            "save_config", "center_camera", "plot_log", "export_log", "reset_logger"
        ],
        "sliders": [
            "max_speed", "max_omega", "max_steer", "grid_size", "noise_sigma", "servo_max_speed"
        ]
    }
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
        "occupancy_free": [230, 230, 230]
    }
}


def load_config(path: str | Path) -> dict[str, Any]:
    """Load configuration from YAML file."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def deepcopy_config(config: dict | None = None) -> dict:
    """Return a deep copy of DEFAULT_CONFIG merged with user config."""
    base = deepcopy(DEFAULT_CONFIG)
    if config:
        _deep_merge(base, config)
    return base


def _deep_merge(base: dict, overlay: dict) -> None:
    """Recursively merge overlay into base."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = deepcopy(value)