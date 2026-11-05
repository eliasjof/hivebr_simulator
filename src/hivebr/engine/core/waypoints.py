from __future__ import annotations
import numpy as np
from .geometry import distance_between


class WaypointManager:
    def __init__(self, config: dict):
        self.waypoints = []
        self.current_index = 0
        self.goal_tolerance = float(config["waypoints"].get("goal_tolerance", 0.35))
        self.colors = config["colors"]
        self.show_tolerance_circle = bool(config["waypoints"].get("show_tolerance_circle", False))
        self.define_orientation = bool(config["waypoints"].get("define_orientation", False))

    def add_waypoint(self, pos):

        if len(pos) == 2:
            pos = (pos[0], pos[1], np.nan)        

        self.waypoints.append(
            np.array([pos[0], pos[1], pos[2]], dtype=float)
        )

    def clear(self):
        self.waypoints.clear()
        self.current_index = 0

    def has_waypoint(self):
        return self.current_index < len(self.waypoints)

    def get_current_waypoint(self):
        return self.waypoints[self.current_index] if self.has_waypoint() else None

    def update(self, robot_position):
        goal = self.get_current_waypoint()        

        if goal is None:
            return

        if distance_between(robot_position, goal[:2]) < self.goal_tolerance:
            self.current_index += 1

    def insert_waypoint_at_current(self, pos):
        if len(pos) == 2:
            pos = (pos[0], pos[1], np.nan)
        
        wp = np.array([pos[0], pos[1], pos[2]], dtype=float)
        
        # Insere na posição atual, empurrando o anterior para a frente
        self.waypoints.insert(self.current_index, wp)

    def status_text(self):
        return "None" if not self.has_waypoint() else f"{self.current_index + 1}/{len(self.waypoints)}"

    # draw method removed - rendering is handled by frontend