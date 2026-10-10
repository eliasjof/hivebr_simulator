"""hivebr — OpenLab API for single- and multi-robot navigation experiments.

The public API is backend-agnostic and intentionally avoids importing the
pygame-based engine (``hivebr.engine``) at package import time, so the same
user script can later target the physical ROS 2 arena.
"""

from .core import HiveBrAgent, SwarmController, SwarmExperiment
from .state import Command, FleetState, RobotState

__all__ = [
    "HiveBrAgent",
    "SwarmController",
    "SwarmExperiment",
    "Command",
    "FleetState",
    "RobotState",
]

__version__ = "0.1.0"
