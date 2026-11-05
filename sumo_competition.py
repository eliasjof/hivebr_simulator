"""
Robot Sumo Competition - RoboCore Style
=========================================
This example creates a sumo competition where two groups can provide
their own robot control code to compete in a sumo match.

Rules (simplified RoboCore):
- Circular arena (dohyo) with diameter ~1.54m (standard)
- Two robots start on opposite sides
- Goal: push opponent out of the ring
- Match ends when one robot leaves the ring or time limit reached
- Autonomous control only (no remote control)

Usage:
    python sumo_competition.py
"""

import math
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from hivebr import SwarmExperiment, HiveBrAgent
from hivebr.state import RobotState, Command
from hivebr.kinematics import wrap_to_pi


# ============================================================
# SUMO ARENA CONFIGURATION
# ============================================================

# Standard RoboCore sumo ring dimensions
SUMO_RING_DIAMETER = 1.54  # meters
SUMO_RING_RADIUS = SUMO_RING_DIAMETER / 2.0
SUMO_RING_BORDER_WIDTH = 0.05  # white border width (5cm)
START_DISTANCE_FROM_CENTER = 0.5  # starting distance from center

# Robot specifications (must comply with RoboCore limits)
MAX_ROBOT_WEIGHT = 3.0  # kg (Mini Sumo)
MAX_ROBOT_WIDTH = 0.20  # 20cm
MAX_ROBOT_DEPTH = 0.20  # 20cm
MAX_ROBOT_HEIGHT = 0.20  # 20cm (no limit in some categories)


@dataclass
class SumoConfig:
    """Configuration for the sumo competition."""
    ring_radius: float = SUMO_RING_RADIUS
    ring_border_width: float = SUMO_RING_BORDER_WIDTH
    start_distance: float = START_DISTANCE_FROM_CENTER
    match_duration: float = 30.0  # seconds
    max_speed: float = 3.0  # m/s
    max_omega: float = 6.0  # rad/s
    robot_radius: float = 0.10  # 10cm radius (20cm diameter)
    dt: float = 0.03  # simulation timestep


# ============================================================
# SUMO ROBOT AGENT BASE CLASS
# ============================================================

class SumoAgent(HiveBrAgent):
    """
    Base class for sumo robot agents.
    
    Groups should extend this class and implement the `loop` method
    with their competition strategy.
    """
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.sumo_config = SumoConfig()
        self.opponent_id: Optional[int] = None
        self.match_start_time: float = 0.0
        self.last_opponent_position: Optional[Tuple[float, float]] = None
        self.is_out_of_ring: bool = False
        
    def set_opponent(self, opponent_id: int):
        """Set the opponent robot ID."""
        self.opponent_id = opponent_id
        
    def is_in_ring(self, x: float, y: float, radius: float = None) -> bool:
        """Check if a position is inside the sumo ring."""
        if radius is None:
            radius = self.sumo_config.ring_radius - self.sumo_config.robot_radius
        return (x * x + y * y) <= (radius * radius)
    
    def distance_to_opponent(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Optional[float]:
        """Get distance to opponent robot."""
        if self.opponent_id is None or self.opponent_id not in neighbors:
            return None
        opp = neighbors[self.opponent_id]
        return math.hypot(state.x - opp.x, state.y - opp.y)
    
    def angle_to_opponent(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Optional[float]:
        """Get angle to opponent robot relative to robot's heading."""
        if self.opponent_id is None or self.opponent_id not in neighbors:
            return None
        opp = neighbors[self.opponent_id]
        dx = opp.x - state.x
        dy = opp.y - state.y
        absolute_angle = math.atan2(dy, dx)
        relative_angle = wrap_to_pi(absolute_angle - state.theta)
        return relative_angle
    
    def get_opponent_state(self, neighbors: Dict[int, RobotState]) -> Optional[RobotState]:
        """Get opponent's robot state."""
        if self.opponent_id is None or self.opponent_id not in neighbors:
            return None
        return neighbors[self.opponent_id]
    
    def time_elapsed(self, state: RobotState) -> float:
        """Get time elapsed since match start (approximate from simulation)."""
        # Using a simple heuristic based on distance traveled
        return self.match_start_time


# ============================================================
# EXAMPLE AGENT IMPLEMENTATIONS (Template for Groups)
# ============================================================

class AggressiveSumoAgent(SumoAgent):
    """
    Example aggressive strategy: Charge directly at opponent.
    This is a simple baseline - groups should implement better strategies!
    """
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.charge_speed = self.sumo_config.max_speed
        self.turn_speed = self.sumo_config.max_omega
        
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        # Check if we're out of ring
        if not self.is_in_ring(state.x, state.y):
            self.is_out_of_ring = True
            return Command(v=0.0, omega=0.0)
        
        # Find opponent
        opp_state = self.get_opponent_state(neighbors)
        if opp_state is None:
            # No opponent visible - spin to search
            return Command(v=0.0, omega=self.turn_speed * 0.5)
        
        # Calculate angle and distance to opponent
        rel_angle = self.angle_to_opponent(state, neighbors)
        distance = self.distance_to_opponent(state, neighbors)
        
        if rel_angle is None or distance is None:
            return Command(v=0.0, omega=self.turn_speed * 0.3)
        
        # Strategy: Turn toward opponent, then charge
        angle_threshold = 0.3  # radians (~17 degrees)
        
        if abs(rel_angle) > angle_threshold:
            # Turn toward opponent
            turn_dir = 1.0 if rel_angle > 0 else -1.0
            return Command(v=0.0, omega=turn_dir * self.turn_speed)
        else:
            # Charge forward
            # Slow down if very close to avoid overshooting
            speed = self.charge_speed
            if distance < 0.3:
                speed = self.charge_speed * 0.7
            return Command(v=speed, omega=0.0)


class DefensiveSumoAgent(SumoAgent):
    """
    Example defensive strategy: Stay near center, push when opponent approaches.
    """
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.center_speed = 1.0
        self.push_speed = 2.5
        self.turn_speed = self.sumo_config.max_omega
        self.defense_radius = 0.4  # stay within this radius of center
        
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        # Check if we're out of ring
        if not self.is_in_ring(state.x, state.y):
            self.is_out_of_ring = True
            return Command(v=0.0, omega=0.0)
        
        # Distance from center
        dist_from_center = math.hypot(state.x, state.y)
        
        # Find opponent
        opp_state = self.get_opponent_state(neighbors)
        
        if opp_state is None:
            # No opponent - return to center
            return self._go_to_center(state, dist_from_center)
        
        rel_angle = self.angle_to_opponent(state, neighbors)
        distance = self.distance_to_opponent(state, neighbors)
        
        if rel_angle is None or distance is None:
            return self._go_to_center(state, dist_from_center)
        
        # If opponent is close, engage
        if distance < 0.6:
            return self._engage_opponent(state, rel_angle, distance)
        else:
            # Opponent far - maintain defensive position near center
            return self._go_to_center(state, dist_from_center)
    
    def _go_to_center(self, state: RobotState, dist_from_center: float) -> Command:
        """Navigate back to center of ring."""
        if dist_from_center < 0.1:
            # At center, face a default direction (e.g., toward +x)
            target_angle = 0.0
            rel_angle = wrap_to_pi(target_angle - state.theta)
            if abs(rel_angle) > 0.1:
                return Command(v=0.0, omega=self.turn_speed * (1.0 if rel_angle > 0 else -1.0))
            return Command(v=0.0, omega=0.0)
        
        # Move toward center
        angle_to_center = math.atan2(-state.y, -state.x)
        rel_angle = wrap_to_pi(angle_to_center - state.theta)
        
        if abs(rel_angle) > 0.3:
            turn_dir = 1.0 if rel_angle > 0 else -1.0
            return Command(v=0.0, omega=turn_dir * self.turn_speed)
        else:
            return Command(v=self.center_speed, omega=0.0)
    
    def _engage_opponent(self, state: RobotState, rel_angle: float, distance: float) -> Command:
        """Engage opponent when close."""
        angle_threshold = 0.2
        
        if abs(rel_angle) > angle_threshold:
            turn_dir = 1.0 if rel_angle > 0 else -1.0
            return Command(v=0.0, omega=turn_dir * self.turn_speed)
        else:
            # Push forward
            return Command(v=self.push_speed, omega=0.0)


class SensorBasedSumoAgent(SumoAgent):
    """
    Example using LiDAR-like sensor data for more sophisticated behavior.
    This simulates what a robot with distance sensors could do.
    """
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.max_speed = self.sumo_config.max_speed
        self.max_omega = self.sumo_config.max_omega
        
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            self.is_out_of_ring = True
            return Command(v=0.0, omega=0.0)
        
        opp_state = self.get_opponent_state(neighbors)
        if opp_state is None:
            return Command(v=0.0, omega=self.max_omega * 0.4)
        
        rel_angle = self.angle_to_opponent(state, neighbors)
        distance = self.distance_to_opponent(state, neighbors)
        
        if rel_angle is None or distance is None:
            return Command(v=0.0, omega=self.max_omega * 0.3)
        
        # More sophisticated behavior:
        # - If opponent is to the side, turn to face
        # - If opponent is ahead, charge
        # - If near edge, prioritize moving away from edge
        dist_from_center = math.hypot(state.x, state.y)
        ring_margin = self.sumo_config.ring_radius - self.sumo_config.robot_radius - dist_from_center
        
        # Edge avoidance
        if ring_margin < 0.3:
            # Near edge - move toward center
            angle_to_center = math.atan2(-state.y, -state.x)
            rel_to_center = wrap_to_pi(angle_to_center - state.theta)
            if abs(rel_to_center) > 0.3:
                return Command(v=0.0, omega=self.max_omega * (1.0 if rel_to_center > 0 else -1.0))
            return Command(v=1.5, omega=0.0)
        
        # Normal engagement
        if abs(rel_angle) > 0.25:
            turn_dir = 1.0 if rel_angle > 0 else -1.0
            return Command(v=0.5, omega=turn_dir * self.max_omega * 0.8)
        else:
            # Charge with speed based on distance
            speed = min(self.max_speed, max(1.0, distance * 3.0))
            return Command(v=speed, omega=0.0)


# ============================================================
# GROUP TEMPLATE - Replace these with your own implementations!
# ============================================================

# GROUP 1: Replace this class with your team's strategy
class Group1Agent(AggressiveSumoAgent):
    """GROUP 1: Implement your sumo strategy here!"""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        # Add your custom parameters here
        self.team_name = "Group 1"
        
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        # TODO: Implement your Group 1 strategy here
        # You have access to:
        # - state: your robot's state (x, y, theta, v, omega, etc.)
        # - neighbors: dict of visible opponent robots with their states
        # - self.sumo_config: arena and robot parameters
        # - self.is_in_ring(x, y): check if position is in ring
        # - self.distance_to_opponent(), self.angle_to_opponent()
        
        # Example: Call parent implementation (replace with your own!)
        return super().loop(state, neighbors)


# GROUP 2: Replace this class with your team's strategy  
class Group2Agent(SensorBasedSumoAgent):
    """GROUP 2: Implement your sumo strategy here!"""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Group 2"
        
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        # TODO: Implement your Group 2 strategy here
        return super().loop(state, neighbors)


# ============================================================
# SUMO COMPETITION MANAGER
# ============================================================

class SumoCompetition:
    """Manages the sumo competition between two robots."""
    
    def __init__(self, config: SumoConfig = None):
        self.config = config or SumoConfig()
        self.experiment: Optional[SwarmExperiment] = None
        self.robot1_id = 0
        self.robot2_id = 1
        self.match_results = {
            "winner": None,
            "reason": None,
            "duration": 0.0,
            "robot1_out": False,
            "robot2_out": False
        }
        
    def create_arena_config(self) -> dict:
        """Create the simulation configuration with sumo ring."""
        # Create circular boundary using obstacles
        # We'll create a ring of obstacles to form the circular boundary
        num_segments = 36
        obstacles = []
        
        for i in range(num_segments):
            angle = 2 * math.pi * i / num_segments
            # Place obstacles just outside the ring to act as boundary
            r = self.config.ring_radius + self.config.robot_radius + 0.02
            x = r * math.cos(angle)
            y = r * math.sin(angle)
            obstacles.append([x, y, 0.04])  # small obstacle segments
        
        config = {
            "window": {
                "width": 1000,
                "height": 800,
                "min_width": 1000,
                "min_height": 650,
                "panel_width": 300,
                "title": "Robot Sumo Competition - RoboCore Style"
            },
            "world": {
                "width": 4.0,
                "height": 4.0,
                "grid_size": 0.5,
                "show_origin": True,
                "show_axes": True,
                "default_obstacle_radius": 0.4,
                "obstacles": obstacles
            },
            "camera": {
                "initial_zoom": 1.5, "min_zoom": 0.25, "max_zoom": 8.0,
                "zoom_step": 1.1, "margin_x": 1.0, "margin_y": 1.0
            },
            "robot": {
                "type": "differential",
                "radius": self.config.robot_radius,
                "length": 0.20,
                "width": 0.20,
                "wheel_base": 0.16,
                "max_speed": self.config.max_speed,
                "max_omega": self.config.max_omega,
                "max_steer": 0.52,
                "path_max_length": 2000,
                "tau_v": 0.2
            },
            "colors": {
                "background": [30, 30, 40],
                "grid": [50, 50, 70],
                "panel": [20, 20, 30],
                "robot": [30, 144, 255],
                "obstacle": [255, 255, 255],  # White ring boundary
                "waypoint": [255, 140, 0],
                "goal": [57, 255, 20],
                "path": [30, 144, 255],
                "lidar": [0, 255, 255],
                "red": [220, 50, 50],
                "green": [0, 255, 0],
                "white": [255, 255, 255],
                "black": [0, 0, 0],
                "silver": [192, 192, 186],
                "fleet": [
                    [30, 144, 255],   # Robot 1 - Blue
                    [220, 20, 60]     # Robot 2 - Red
                ]
            },
            "interaction": {
                "collision_policy": "resolve",
                "robot_collision": True,
                "robot_safety_margin": 0.0,
                "resolve_push": 0.08,
                "comm_radius": 3.0,
                "show_robot_links": False
            },
            "lidar": {
                "enabled": True,
                "num_rays": 36,
                "range": 2.0,
                "fov_deg": 360
            },
            "noise": {
                "enabled": False,
                "sigma_v": 0.0,
                "sigma_omega": 0.0,
                "limit": 3.0
            },
            "controller": {
                "enabled": False
            },
            "waypoints": {
                "goal_tolerance": 0.5,
                "define_orientation": False,
                "show_tolerance_circle": False,
                "points": []
            },
            "theme": "dark",
            "running_simulation": False
        }
        return config
    
    def setup_robots(self, agent1_class, agent2_class):
        """Set up the two robots with their agents."""
        config = self.create_arena_config()
        
        # Starting positions: opposite sides on Y-axis, facing each other
        r = self.config.start_distance
        robot1_pos = [0.0, r, -math.pi/2]   # Top, facing down
        robot2_pos = [0.0, -r, math.pi/2]   # Bottom, facing up
        
        # Fleet configuration with two robots
        config["robots"] = [
            {"id": self.robot1_id, "initial_pose": robot1_pos, "color": [30, 144, 255]},
            {"id": self.robot2_id, "initial_pose": robot2_pos, "color": [220, 20, 60]}
        ]
        
        # Create experiment
        self.experiment = SwarmExperiment(
            robots=config["robots"],
            backend="navsim2d",
            config=config,
            dt=self.config.dt,
            comm_radius=3.0
        )
        
        # Assign agents
        self.experiment.assign_agent(robot_id=self.robot1_id, agent_class=agent1_class)
        self.experiment.assign_agent(robot_id=self.robot2_id, agent_class=agent2_class)
        
        # Set opponents for each agent
        # We need to do this after agents are created
        return self.experiment
    
    def run_match(self, agent1_class, agent2_class, headless: bool = False) -> dict:
        """Run a single sumo match."""
        self.experiment = self.setup_robots(agent1_class, agent2_class)
        
        # Get agents after they're created
        self.experiment._build()
        agent1 = self.experiment.agents.get(self.robot1_id)
        agent2 = self.experiment.agents.get(self.robot2_id)
        
        if agent1 and agent2:
            agent1.set_opponent(self.robot2_id)
            agent2.set_opponent(self.robot1_id)
        
        if headless:
            # Run without GUI for faster batch testing
            return self._run_headless()
        else:
            # Run with GUI
            self.experiment.run()
            return self.match_results
    
    def _run_headless(self) -> dict:
        """Run match without GUI for automated testing."""
        # This would require modifying the backend to support headless mode
        # For now, return placeholder
        return self.match_results


def create_sumo_arena_image(filename: str = "sumo_ring.png", 
                             diameter: float = 1.54,
                             resolution: float = 0.01,
                             border_width: float = 0.05) -> str:
    """
    Create a sumo ring image for use as a map.
    White = free space, Black = obstacle (outside ring)
    """
    from PIL import Image, ImageDraw
    
    # Add margin around ring
    margin = 0.5
    world_size = diameter + 2 * margin
    pixels_per_meter = int(1.0 / resolution)
    size_px = int(world_size * pixels_per_meter)
    
    # Create image (white background = free)
    img = Image.new("L", (size_px, size_px), 255)
    draw = ImageDraw.Draw(img)
    
    center = size_px // 2
    ring_radius_px = int((diameter / 2) * pixels_per_meter)
    border_px = int(border_width * pixels_per_meter)
    
    # Draw outer boundary (black = obstacle)
    outer_radius = ring_radius_px + border_px
    draw.ellipse([
        center - outer_radius, center - outer_radius,
        center + outer_radius, center + outer_radius
    ], outline=0, width=border_px)
    
    # Draw inner boundary (the white line on the ring)
    inner_radius = ring_radius_px - border_px
    draw.ellipse([
        center - inner_radius, center - inner_radius,
        center + inner_radius, center + inner_radius
    ], outline=128, width=2)
    
    # The area OUTSIDE the ring should be black (obstacle)
    # Draw four rectangles covering the corners
    # Top
    draw.rectangle([0, 0, size_px, center - outer_radius], fill=0)
    # Bottom
    draw.rectangle([0, center + outer_radius, size_px, size_px], fill=0)
    # Left
    draw.rectangle([0, center - outer_radius, center - outer_radius, center + outer_radius], fill=0)
    # Right
    draw.rectangle([center + outer_radius, center - outer_radius, size_px, center + outer_radius], fill=0)
    
    img.save(filename)
    print(f"Sumo ring map saved to {filename}")
    print(f"  World size: {world_size:.2f}m x {world_size:.2f}m")
    print(f"  Resolution: {resolution}m/pixel")
    print(f"  Ring diameter: {diameter}m")
    return filename


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Run the sumo competition with the two group agents."""
    print("=" * 60)
    print("ROBOT SUMO COMPETITION - RoboCore Style")
    print("=" * 60)
    print()
    print("Group 1 (Blue) vs Group 2 (Red)")
    print(f"Ring diameter: {SUMO_RING_DIAMETER}m")
    print(f"Match duration: 30 seconds")
    print()
    
    # Create config
    config = SumoConfig()
    
    # Create competition
    competition = SumoCompetition(config)
    
    # Run match with GUI
    print("Starting match...")
    print("Press 'R' to reset, 'SPACE' to pause/unpause, 'ESC' to quit")
    print()
    
    try:
        competition.run_match(Group1Agent, Group2Agent, headless=False)
    except KeyboardInterrupt:
        print("\nMatch interrupted by user.")
    except Exception as e:
        print(f"\nError during match: {e}")
        import traceback
        traceback.print_exc()


def create_arena_map():
    """Utility to create the sumo ring map image."""
    create_sumo_arena_image("config/sumo_ring.png")
    
    # Also create a config file that uses this map
    import yaml
    
    map_config = {
        "window": {"width": 1000, "height": 800, "title": "Robot Sumo - Map Based"},
        "world": {
            "width": 2.54, "height": 2.54, "grid_size": 0.5,
            "map_image": "config/sumo_ring.png",
            "resolution": 0.01,
            "show_origin": True
        },
        "robot": {
            "type": "differential",
            "radius": 0.10, "length": 0.20, "width": 0.20,
            "wheel_base": 0.16, "max_speed": 3.0, "max_omega": 6.0
        },
        "robots": [
            {"id": 0, "initial_pose": [0.5, 0.0, 1.57], "color": [30, 144, 255]},
            {"id": 1, "initial_pose": [-0.5, 0.0, -1.57], "color": [220, 20, 60]}
        ],
        "interaction": {
            "collision_policy": "resolve", "robot_collision": True,
            "robot_safety_margin": 0.0, "resolve_push": 0.08,
            "comm_radius": 3.0
        },
        "lidar": {"enabled": True, "num_rays": 36, "range": 2.0, "fov_deg": 360}
    }
    
    with open("config/sumo_competition.yaml", "w") as f:
        yaml.dump(map_config, f, sort_keys=False)
    
    print("Created config/sumo_competition.yaml")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "create-map":
        create_arena_map()
    else:
        main()