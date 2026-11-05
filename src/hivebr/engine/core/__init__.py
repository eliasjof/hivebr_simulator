"""
hivebr.engine.core - Pure Python simulation core (no pygame dependency).

This module contains all the simulation logic extracted from the pygame-based
engine, designed to run in Pyodide/WASM or headless on a server.
"""

from .simulator_core import SimulatorCore, SimStepResult
from .world import World
from .robots import create_robot, create_fleet
from .lidar import Lidar
from .waypoints import WaypointManager
from .track_editor import TrackEditor
from .occupancy_grid import OccupancyGridMap
from .line_map import LineTrackMap
from .data_logger import DataLogger, Frame, SimLog, MultiRobotLog
from .config import DEFAULT_CONFIG, THEMES, load_config
from .geometry import wrap_to_pi, clamp, distance_between
from .interaction import detect_robot_collisions, resolve_robot_overlaps, build_neighbors

__all__ = [
    "SimulatorCore",
    "SimStepResult",
    "World",
    "create_robot",
    "create_fleet",
    "Lidar",
    "WaypointManager",
    "TrackEditor",
    "OccupancyGridMap",
    "LineTrackMap",
    "DataLogger",
    "Frame",
    "SimLog",
    "MultiRobotLog",
    "DEFAULT_CONFIG",
    "THEMES",
    "load_config",
    "wrap_to_pi",
    "clamp",
    "distance_between",
    "detect_robot_collisions",
    "resolve_robot_overlaps",
    "build_neighbors",
]