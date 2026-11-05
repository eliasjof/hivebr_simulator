"""
Robot Sumo Competition - Advanced Version with Custom Rendering
================================================================
This version includes a custom draw callback to render the sumo ring
properly with the white border (shikiri-sen) and starting lines.
"""

import math
import numpy as np
import pygame
from typing import Dict, Optional, Tuple

from hivebr import SwarmExperiment, HiveBrAgent
from hivebr.state import RobotState, Command
from hivebr.kinematics import wrap_to_pi


# ============================================================
# SUMO RING RENDERING
# ============================================================

def draw_sumo_ring(simulator, screen):
    """
    Custom draw callback to render the sumo ring with proper markings.
    
    RoboCore sumo ring specifications:
    - Diameter: 1.54m (77cm radius)
    - White border (shikiri-sen): 5cm wide
    - Two starting lines (shikiri-sen): 20cm long, 10cm from center, 70cm apart
    - Surface: Black (or dark color)
    """
    c = simulator.config["colors"]
    camera = simulator.camera
    
    # Ring parameters
    ring_radius = 0.77  # 1.54m diameter / 2
    border_width = 0.05  # 5cm white border
    ring_color = (30, 30, 30)      # Dark ring surface
    border_color = (255, 255, 255) # White border
    line_color = (255, 255, 255)   # White starting lines
    
    # Draw ring surface (dark circle)
    center_screen = camera.world_to_screen(0, 0)
    ring_radius_px = max(5, int(ring_radius * camera.scale))
    
    pygame.draw.circle(screen, ring_color, center_screen, ring_radius_px)
    
    # Draw white border (shikiri-sen)
    outer_radius_px = max(5, int((ring_radius + border_width/2) * camera.scale))
    inner_radius_px = max(5, int((ring_radius - border_width/2) * camera.scale))
    border_thickness_px = max(2, outer_radius_px - inner_radius_px)
    
    pygame.draw.circle(screen, border_color, center_screen, outer_radius_px, border_thickness_px)
    
    # Draw starting lines (shikiri-sen) - two parallel lines
    # Each line is 20cm long, centered 10cm from center, 70cm apart (35cm each side)
    line_length = 0.20  # 20cm
    line_distance_from_center = 0.10  # 10cm from center
    line_separation = 0.70  # 70cm apart (35cm each side)
    line_width = 0.02  # 2cm wide
    
    for side in [-1, 1]:  # Left and right starting positions
        y_offset = side * line_separation / 2
        
        # Line endpoints in world coordinates
        x1 = -line_length / 2
        x2 = line_length / 2
        y = y_offset
        
        # Convert to screen coordinates
        p1 = camera.world_to_screen(x1, y)
        p2 = camera.world_to_screen(x2, y)
        
        line_width_px = max(2, int(line_width * camera.scale))
        pygame.draw.line(screen, line_color, p1, p2, line_width_px)
    
    # Draw center cross for reference
    cross_size = max(5, int(0.1 * camera.scale))
    pygame.draw.line(screen, (100, 100, 100), 
                     (center_screen[0] - cross_size, center_screen[1]),
                     (center_screen[0] + cross_size, center_screen[1]), 1)
    pygame.draw.line(screen, (100, 100, 100),
                     (center_screen[0], center_screen[1] - cross_size),
                     (center_screen[0], center_screen[1] + cross_size), 1)


# ============================================================
# ADVANCED SUMO AGENTS WITH BETTER STRATEGIES
# ============================================================

class AdvancedSumoAgent(HiveBrAgent):
    """
    Advanced base agent with more sophisticated behaviors:
    - Edge detection and avoidance
    - Opponent tracking with prediction
    - State machine for different behaviors
    - LiDAR integration for local obstacle avoidance
    """
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        
        # Robot parameters
        self.robot_radius = 0.10
        self.ring_radius = 0.77
        self.max_speed = 3.0
        self.max_omega = 6.0
        
        # State machine
        self.state = "SEARCH"  # SEARCH, APPROACH, ATTACK, DEFEND, RETREAT
        self.state_timer = 0.0
        
        # Opponent tracking
        self.opponent_id: Optional[int] = None
        self.last_opp_pos: Optional[Tuple[float, float]] = None
        self.last_opp_time: float = 0.0
        self.opp_velocity: Tuple[float, float] = (0.0, 0.0)
        
        # Behavioral parameters
        self.attack_distance = 0.5
        self.defend_distance = 0.8
        self.edge_margin = 0.15
        self.search_omega = 2.0
        self.approach_speed = 1.5
        self.attack_speed = 3.0
        self.retreat_speed = 2.0
        
    def set_opponent(self, opponent_id: int):
        self.opponent_id = opponent_id
    
    def is_in_ring(self, x: float, y: float, margin: float = 0.0) -> bool:
        effective_radius = self.ring_radius - self.robot_radius - margin
        return (x * x + y * y) <= (effective_radius * effective_radius)
    
    def distance_to_center(self, state: RobotState) -> float:
        return math.hypot(state.x, state.y)
    
    def angle_to_center(self, state: RobotState) -> float:
        return math.atan2(-state.y, -state.x)
    
    def get_opponent(self, neighbors: Dict[int, RobotState]) -> Optional[RobotState]:
        if self.opponent_id is None or self.opponent_id not in neighbors:
            return None
        return neighbors[self.opponent_id]
    
    def update_opponent_tracking(self, state: RobotState, neighbors: Dict[int, RobotState], dt: float):
        """Track opponent position and estimate velocity."""
        opp = self.get_opponent(neighbors)
        if opp is None:
            return
        
        current_time = state.v * 0.03  # Approximate time
        current_pos = (opp.x, opp.y)
        
        if self.last_opp_pos is not None and self.last_opp_time > 0:
            dt_track = current_time - self.last_opp_time
            if dt_track > 0:
                vx = (current_pos[0] - self.last_opp_pos[0]) / dt_track
                vy = (current_pos[1] - self.last_opp_pos[1]) / dt_track
                # Smooth velocity estimate
                alpha = 0.3
                self.opp_velocity = (
                    alpha * vx + (1 - alpha) * self.opp_velocity[0],
                    alpha * vy + (1 - alpha) * self.opp_velocity[1]
                )
        
        self.last_opp_pos = current_pos
        self.last_opp_time = current_time
    
    def predict_opponent_position(self, lookahead: float = 0.5) -> Optional[Tuple[float, float]]:
        """Predict where opponent will be in `lookahead` seconds."""
        if self.last_opp_pos is None:
            return None
        return (
            self.last_opp_pos[0] + self.opp_velocity[0] * lookahead,
            self.last_opp_pos[1] + self.opp_velocity[1] * lookahead
        )
    
    def angle_to_target(self, state: RobotState, target_x: float, target_y: float) -> float:
        absolute = math.atan2(target_y - state.y, target_x - state.x)
        return wrap_to_pi(absolute - state.theta)
    
    def distance_to_target(self, state: RobotState, target_x: float, target_y: float) -> float:
        return math.hypot(target_x - state.x, target_y - state.y)
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        """Main control loop - implement state machine."""
        dt = 0.03
        self.state_timer += dt
        
        # Update opponent tracking
        self.update_opponent_tracking(state, neighbors, dt)
        
        # Check if out of ring
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        # Get opponent info
        opp = self.get_opponent(neighbors)
        has_opponent = opp is not None
        
        if has_opponent:
            opp_dist = math.hypot(state.x - opp.x, state.y - opp.y)
            opp_angle = self.angle_to_target(state, opp.x, opp.y)
        else:
            opp_dist = float('inf')
            opp_angle = 0.0
        
        dist_center = self.distance_to_center(state)
        edge_margin = self.ring_radius - self.robot_radius - dist_center
        
        # State machine transitions
        self._update_state(has_opponent, opp_dist, opp_angle, dist_center, edge_margin)
        
        # Execute behavior based on state
        return self._execute_state(state, has_opponent, opp_dist, opp_angle, dist_center, edge_margin)
    
    def _update_state(self, has_opponent: bool, opp_dist: float, opp_angle: float, 
                      dist_center: float, edge_margin: float):
        """Update behavioral state."""
        prev_state = self.state
        
        # Priority 1: Edge avoidance
        if edge_margin < self.edge_margin:
            self.state = "RETREAT"
        # Priority 2: Opponent engagement
        elif has_opponent:
            if opp_dist < self.attack_distance:
                self.state = "ATTACK"
            elif opp_dist < self.defend_distance:
                self.state = "APPROACH"
            else:
                self.state = "SEARCH"
        # Priority 3: Center control
        elif dist_center > 0.4:
            self.state = "DEFEND"  # Return to center
        else:
            self.state = "SEARCH"
        
        # Reset timer on state change
        if self.state != prev_state:
            self.state_timer = 0.0
    
    def _execute_state(self, state: RobotState, has_opponent: bool, opp_dist: float,
                       opp_angle: float, dist_center: float, edge_margin: float) -> Command:
        """Execute behavior for current state."""
        
        if self.state == "SEARCH":
            # Spin slowly to search for opponent
            return Command(v=0.0, omega=self.search_omega)
        
        elif self.state == "APPROACH":
            # Move toward opponent
            if abs(opp_angle) > 0.3:
                turn = self.max_omega if opp_angle > 0 else -self.max_omega
                return Command(v=0.5, omega=turn)
            return Command(v=self.approach_speed, omega=0.0)
        
        elif self.state == "ATTACK":
            # Charge at opponent with prediction
            pred_pos = self.predict_opponent_position(0.3)
            if pred_pos:
                target_angle = self.angle_to_target(state, pred_pos[0], pred_pos[1])
            else:
                target_angle = opp_angle
            
            if abs(target_angle) > 0.2:
                turn = self.max_omega if target_angle > 0 else -self.max_omega
                return Command(v=1.0, omega=turn)
            return Command(v=self.attack_speed, omega=0.0)
        
        elif self.state == "DEFEND":
            # Move to center and face outward
            angle_to_center = self.angle_to_center(state)
            if abs(angle_to_center) > 0.3:
                turn = self.max_omega if angle_to_center > 0 else -self.max_omega
                return Command(v=0.0, omega=turn)
            return Command(v=1.0, omega=0.0)
        
        elif self.state == "RETREAT":
            # Move away from edge toward center
            angle_to_center = self.angle_to_center(state)
            if abs(angle_to_center) > 0.2:
                turn = self.max_omega if angle_to_center > 0 else -self.max_omega
                return Command(v=0.5, omega=turn)
            return Command(v=self.retreat_speed, omega=0.0)
        
        return Command(v=0.0, omega=0.0)


# ============================================================
# GROUP AGENT TEMPLATES
# ============================================================

class Group1Agent(AdvancedSumoAgent):
    """GROUP 1: Customize this agent for your strategy!"""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Group 1 - Blue"
        # Customize parameters for your strategy:
        self.attack_distance = 0.6
        self.defend_distance = 0.9
        self.edge_margin = 0.2
        self.attack_speed = 3.0
        self.approach_speed = 2.0
        
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        """Override with your custom strategy!"""
        # Call parent for base behavior, or implement completely custom logic
        return super().loop(state, neighbors)


class Group2Agent(AdvancedSumoAgent):
    """GROUP 2: Customize this agent for your strategy!"""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Group 2 - Red"
        # Different parameters for different strategy:
        self.attack_distance = 0.5
        self.defend_distance = 0.8
        self.edge_margin = 0.15
        self.attack_speed = 2.8
        self.approach_speed = 1.8
        self.search_omega = 1.5  # Slower search
        
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        """Override with your custom strategy!"""
        return super().loop(state, neighbors)


# ============================================================
# MAIN COMPETITION RUNNER
# ============================================================

def create_competition_config() -> dict:
    """Create full simulation configuration for sumo competition."""
    
    # Create circular boundary obstacles
    num_segments = 48
    obstacles = []
    ring_radius = 0.77
    robot_radius = 0.10
    
    for i in range(num_segments):
        angle = 2 * math.pi * i / num_segments
        # Obstacles just outside ring to enforce boundary
        r = ring_radius + robot_radius + 0.015
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        obstacles.append([x, y, 0.025])
    
    config = {
        "window": {
            "width": 1200,
            "height": 900,
            "min_width": 1000,
            "min_height": 700,
            "panel_width": 350,
            "title": "Robot Sumo Competition - RoboCore Style"
        },
        "world": {
            "width": 3.0,
            "height": 3.0,
            "grid_size": 0.5,
            "show_origin": True,
            "show_axes": False,
            "default_obstacle_radius": 0.4,
            "obstacles": obstacles
        },
        "camera": {
            "initial_zoom": 1.8, "min_zoom": 0.25, "max_zoom": 8.0,
            "zoom_step": 1.1, "margin_x": 1.0, "margin_y": 1.0
        },
        "robot": {
            "type": "differential",
            "radius": 0.10,
            "length": 0.20,
            "width": 0.20,
            "wheel_base": 0.16,
            "max_speed": 3.0,
            "max_omega": 6.0,
            "max_steer": 0.52,
            "path_max_length": 2000,
            "tau_v": 0.2
        },
        "colors": {
            "background": [20, 20, 30],
            "grid": [40, 40, 55],
            "panel": [15, 15, 25],
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
                [30, 144, 255],    # Robot 1 - Blue (DodgerBlue)
                [220, 20, 60]      # Robot 2 - Red (Crimson)
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
            "num_rays": 72,
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


def run_competition(agent1_class=Group1Agent, agent2_class=Group2Agent, 
                    headless: bool = False, duration: float = 30.0):
    """Run the sumo competition."""
    
    config = create_competition_config()
    
    # Starting positions: opposite sides on Y-axis, facing each other
    start_dist = 0.45
    robot1_pos = [0.0, start_dist, -math.pi/2]   # Top, facing down
    robot2_pos = [0.0, -start_dist, math.pi/2]   # Bottom, facing up
    
    config["robots"] = [
        {"id": 0, "initial_pose": robot1_pos, "color": [30, 144, 255]},
        {"id": 1, "initial_pose": robot2_pos, "color": [220, 20, 60]}
    ]
    
    # Create experiment
    experiment = SwarmExperiment(
        robots=config["robots"],
        backend="navsim2d",
        config=config,
        dt=0.03,
        comm_radius=3.0
    )
    
    # Assign agents
    experiment.assign_agent(robot_id=0, agent_class=agent1_class)
    experiment.assign_agent(robot_id=1, agent_class=agent2_class)
    
    # Build to create agents
    experiment._build()
    
    # Set up opponent references
    agent1 = experiment.agents.get(0)
    agent2 = experiment.agents.get(1)
    
    if agent1 and agent2:
        agent1.set_opponent(1)
        agent2.set_opponent(0)
        print(f"Team 1: {agent1.team_name}")
        print(f"Team 2: {agent2.team_name}")
    
    # Add custom draw callback for sumo ring
    from hivebr.engine import Simulator
    
    original_build = experiment._ensure_backend
    
    def custom_build():
        backend = original_build()
        if hasattr(backend, '_sim') and backend._sim:
            backend._sim.draw_callback = draw_sumo_ring
        return backend
    
    experiment._ensure_backend = custom_build
    
    print("\n" + "=" * 60)
    print("ROBOT SUMO COMPETITION STARTING")
    print("=" * 60)
    print("Controls:")
    print("  SPACE  - Pause/Resume")
    print("  R      - Reset match")
    print("  1/2    - Select robot 1/2")
    print("  ESC    - Quit")
    print("=" * 60 + "\n")
    
    try:
        experiment.run()
    except KeyboardInterrupt:
        print("\nCompetition ended by user.")
    
    return experiment


def run_tournament(agent1_class, agent2_class, num_matches: int = 5):
    """Run a tournament with multiple matches."""
    print(f"\nStarting tournament: {num_matches} matches")
    print(f"Group 1: {agent1_class.__name__} vs Group 2: {agent2_class.__name__}")
    
    results = {"group1_wins": 0, "group2_wins": 0, "draws": 0}
    
    for match_num in range(1, num_matches + 1):
        print(f"\n--- Match {match_num}/{num_matches} ---")
        # Note: Full headless tournament would require backend modifications
        # For now, run with GUI
        run_competition(agent1_class, agent2_class)
        
        # In a real tournament, you'd check results automatically
        # For now, manual scoring
        winner = input("Winner (1/2/draw): ").strip()
        if winner == "1":
            results["group1_wins"] += 1
        elif winner == "2":
            results["group2_wins"] += 1
        else:
            results["draws"] += 1
    
    print("\n" + "=" * 40)
    print("TOURNAMENT RESULTS")
    print("=" * 40)
    print(f"Group 1 Wins: {results['group1_wins']}")
    print(f"Group 2 Wins: {results['group2_wins']}")
    print(f"Draws: {results['draws']}")
    print("=" * 40)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "tournament":
            run_tournament(Group1Agent, Group2Agent, num_matches=3)
        elif sys.argv[1] == "group1":
            # Test Group 1 vs basic opponent
            run_competition(Group1Agent, AdvancedSumoAgent)
        elif sys.argv[1] == "group2":
            # Test Group 2 vs basic opponent
            run_competition(AdvancedSumoAgent, Group2Agent)
    else:
        # Default: Group 1 vs Group 2
        run_competition(Group1Agent, Group2Agent)