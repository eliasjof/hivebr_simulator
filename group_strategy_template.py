"""
GROUP STRATEGY TEMPLATE
========================
Copy this file and rename it (e.g., group1_strategy.py, group2_strategy.py)
Implement your sumo robot strategy in the MySumoAgent class.

Each group should provide ONE Python file with their agent implementation.
The competition organizer will import both and run the match.
"""

import math
from typing import Dict, Optional, Tuple

from hivebr import HiveBrAgent
from hivebr.state import RobotState, Command
from hivebr.kinematics import wrap_to_pi


class MySumoAgent(HiveBrAgent):
    """
    Template for a sumo robot agent.
    
    IMPLEMENT YOUR STRATEGY IN THE `loop` METHOD BELOW.
    
    Available information:
    - self.id: Your robot ID (0 or 1)
    - self.opponent_id: Opponent robot ID (set by competition)
    - state: Your robot's current state
    - neighbors: Dict of visible robots (including opponent)
    
    RobotState attributes:
    - state.id, state.x, state.y, state.theta (position and orientation)
    - state.v, state.omega (current velocities)
    - state.radius (robot radius)
    - state.battery (battery level)
    
    Helper methods you can use:
    - self.is_in_ring(x, y): Check if position is inside ring
    - self.distance_to_opponent(state, neighbors): Distance to opponent
    - self.angle_to_opponent(state, neighbors): Relative angle to opponent
    - self.get_opponent_state(neighbors): Get opponent's RobotState
    """
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        
        # === ROBOT & ARENA PARAMETERS ===
        # These match the competition configuration
        self.robot_radius = 0.10        # 10cm radius
        self.ring_radius = 0.77         # 77cm ring radius (1.54m diameter)
        self.max_speed = 3.0            # m/s
        self.max_omega = 6.0            # rad/s
        self.border_width = 0.05        # 5cm white border
        
        # === YOUR CUSTOM PARAMETERS ===
        # Add your strategy parameters here
        self.attack_distance = 0.5
        self.defend_distance = 0.8
        self.edge_margin = 0.15
        self.search_speed = 1.0
        self.attack_speed = 3.0
        
        # === STATE TRACKING ===
        self.opponent_id: Optional[int] = None
        self.last_opp_pos: Optional[Tuple[float, float]] = None
        self.opp_velocity: Tuple[float, float] = (0.0, 0.0)
        self.state = "SEARCH"  # Your state machine states
        self.state_timer = 0.0
        
        # Team identification (for display)
        self.team_name = "My Team"
        self.team_color = [30, 144, 255]  # RGB
    
    def set_opponent(self, opponent_id: int):
        """Called by competition to set opponent ID."""
        self.opponent_id = opponent_id
    
    # === HELPER METHODS ===
    
    def is_in_ring(self, x: float, y: float, margin: float = 0.0) -> bool:
        """Check if position is inside the sumo ring."""
        effective_radius = self.ring_radius - self.robot_radius - margin
        return (x * x + y * y) <= (effective_radius * effective_radius)
    
    def distance_to_center(self, state: RobotState) -> float:
        """Distance from ring center."""
        return math.hypot(state.x, state.y)
    
    def angle_to_center(self, state: RobotState) -> float:
        """Angle pointing toward ring center."""
        return math.atan2(-state.y, -state.x)
    
    def get_opponent(self, neighbors: Dict[int, RobotState]) -> Optional[RobotState]:
        """Get opponent's state if visible."""
        if self.opponent_id is None or self.opponent_id not in neighbors:
            return None
        return neighbors[self.opponent_id]
    
    def distance_to_opponent(self, state: RobotState, 
                             neighbors: Dict[int, RobotState]) -> Optional[float]:
        """Distance to opponent robot."""
        opp = self.get_opponent(neighbors)
        if opp is None:
            return None
        return math.hypot(state.x - opp.x, state.y - opp.y)
    
    def angle_to_opponent(self, state: RobotState,
                          neighbors: Dict[int, RobotState]) -> Optional[float]:
        """Relative angle to opponent (-pi to pi, 0 = straight ahead)."""
        opp = self.get_opponent(neighbors)
        if opp is None:
            return None
        dx = opp.x - state.x
        dy = opp.y - state.y
        absolute = math.atan2(dy, dx)
        return wrap_to_pi(absolute - state.theta)
    
    def angle_to_target(self, state: RobotState, tx: float, ty: float) -> float:
        """Relative angle to arbitrary target."""
        absolute = math.atan2(ty - state.y, tx - state.x)
        return wrap_to_pi(absolute - state.theta)
    
    def update_opponent_tracking(self, neighbors: Dict[int, RobotState], dt: float):
        """Track opponent position and estimate velocity."""
        opp = self.get_opponent(neighbors)
        if opp is None:
            return
        
        current_pos = (opp.x, opp.y)
        
        if self.last_opp_pos is not None:
            vx = (current_pos[0] - self.last_opp_pos[0]) / dt
            vy = (current_pos[1] - self.last_opp_pos[1]) / dt
            # Exponential smoothing
            alpha = 0.3
            self.opp_velocity = (
                alpha * vx + (1 - alpha) * self.opp_velocity[0],
                alpha * vy + (1 - alpha) * self.opp_velocity[1]
            )
        
        self.last_opp_pos = current_pos
    
    def predict_opponent(self, lookahead: float = 0.5) -> Optional[Tuple[float, float]]:
        """Predict opponent position in `lookahead` seconds."""
        if self.last_opp_pos is None:
            return None
        return (
            self.last_opp_pos[0] + self.opp_velocity[0] * lookahead,
            self.last_opp_pos[1] + self.opp_velocity[1] * lookahead
        )
    
    # === MAIN CONTROL LOOP ===
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        """
        MAIN STRATEGY IMPLEMENTATION GOES HERE!
        
        This method is called every simulation step (30ms by default).
        Return a Command(v, omega) with your desired velocities.
        
        Example structure:
        1. Check if out of ring -> stop
        2. Update opponent tracking
        3. Decide behavior based on situation
        4. Return command
        """
        dt = 0.03  # Simulation timestep
        self.state_timer += dt
        
        # 1. CHECK IF OUT OF RING
        if not self.is_in_ring(state.x, state.y):
            # We're out! Stop motors.
            return Command(v=0.0, omega=0.0)
        
        # 2. UPDATE OPPONENT TRACKING
        self.update_opponent_tracking(neighbors, dt)
        
        # 3. GET SITUATION INFO
        opp = self.get_opponent(neighbors)
        has_opponent = opp is not None
        
        if has_opponent:
            opp_dist = self.distance_to_opponent(state, neighbors)
            opp_angle = self.angle_to_opponent(state, neighbors)
        else:
            opp_dist = float('inf')
            opp_angle = 0.0
        
        dist_center = self.distance_to_center(state)
        edge_margin = self.ring_radius - self.robot_radius - dist_center
        
        # 4. IMPLEMENT YOUR STRATEGY HERE
        # ========================================
        # REPLACE THIS EXAMPLE WITH YOUR CODE!
        # ========================================
        
        # Example: Simple state machine
        # (Replace with your own logic)
        
        # Priority: Avoid ring edge
        if edge_margin < self.edge_margin:
            return self._retreat_to_center(state)
        
        if has_opponent:
            if opp_dist < self.attack_distance:
                return self._attack_opponent(state, opp_dist, opp_angle)
            elif opp_dist < self.defend_distance:
                return self._approach_opponent(state, opp_dist, opp_angle)
            else:
                return self._search_pattern(state)
        else:
            # No opponent visible
            if dist_center > 0.4:
                return self._go_to_center(state)
            return self._search_pattern(state)
    
    # === BEHAVIOR METHODS (Customize these!) ===
    
    def _search_pattern(self, state: RobotState) -> Command:
        """Search for opponent by spinning."""
        return Command(v=0.0, omega=self.max_omega * 0.4)
    
    def _approach_opponent(self, state: RobotState, dist: float, angle: float) -> Command:
        """Move toward opponent."""
        if abs(angle) > 0.3:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.5, omega=turn)
        return Command(v=self.search_speed, omega=0.0)
    
    def _attack_opponent(self, state: RobotState, dist: float, angle: float) -> Command:
        """Charge at opponent."""
        # Use prediction for better accuracy
        pred = self.predict_opponent(0.3)
        if pred:
            target_angle = self.angle_to_target(state, pred[0], pred[1])
        else:
            target_angle = angle
        
        if abs(target_angle) > 0.2:
            turn = self.max_omega if target_angle > 0 else -self.max_omega
            return Command(v=1.0, omega=turn)
        return Command(v=self.attack_speed, omega=0.0)
    
    def _go_to_center(self, state: RobotState) -> Command:
        """Navigate to ring center."""
        angle = self.angle_to_center(state)
        if abs(angle) > 0.3:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.0, omega=turn)
        return Command(v=1.5, omega=0.0)
    
    def _retreat_to_center(self, state: RobotState) -> Command:
        """Emergency retreat from ring edge."""
        angle = self.angle_to_center(state)
        if abs(angle) > 0.2:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.5, omega=turn)
        return Command(v=2.0, omega=0.0)


# === EXAMPLE: Alternative Strategy Classes ===

class AggressiveRusher(MySumoAgent):
    """Example: Always charge at opponent."""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Aggressive Rusher"
        self.attack_speed = 3.0
        self.attack_distance = 1.0  # Attack from far away
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        opp = self.get_opponent(neighbors)
        if opp is None:
            return Command(v=0.0, omega=self.max_omega * 0.5)
        
        angle = self.angle_to_opponent(state, neighbors)
        if abs(angle) > 0.2:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=1.0, omega=turn)
        return Command(v=self.attack_speed, omega=0.0)


class DefensiveCenter(MySumoAgent):
    """Example: Stay in center, wait for opponent."""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Defensive Center"
        self.attack_distance = 0.4
        self.defend_distance = 0.6
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        # Always try to stay at center
        dist_center = self.distance_to_center(state)
        opp = self.get_opponent(neighbors)
        
        if opp is None or dist_center > 0.3:
            return self._go_to_center(state)
        
        # Opponent close - push!
        angle = self.angle_to_opponent(state, neighbors)
        if abs(angle) > 0.2:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.0, omega=turn)
        return Command(v=2.5, omega=0.0)


class SensorBasedBot(MySumoAgent):
    """Example: Uses simulated sensor readings for decisions."""
    
    def __init__(self, robot_id: int = None, config: dict = None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Sensor Bot"
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        # In a real robot, you'd read LiDAR/distance sensors here
        # For simulation, we use the opponent state directly
        
        opp = self.get_opponent(neighbors)
        dist_center = self.distance_to_center(state)
        edge_margin = self.ring_radius - self.robot_radius - dist_center
        
        # Edge avoidance (simulating edge sensors)
        if edge_margin < 0.15:
            angle = self.angle_to_center(state)
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=1.5, omega=turn * 0.5)
        
        if opp is None:
            # Patrol pattern
            return Command(v=1.0, omega=0.5)
        
        dist = self.distance_to_opponent(state, neighbors)
        angle = self.angle_to_opponent(state, neighbors)
        
        if dist < 0.4:
            # Close - push hard
            if abs(angle) > 0.15:
                turn = self.max_omega if angle > 0 else -self.max_omega
                return Command(v=1.0, omega=turn)
            return Command(v=3.0, omega=0.0)
        else:
            # Far - approach carefully
            if abs(angle) > 0.3:
                turn = self.max_omega if angle > 0 else -self.max_omega
                return Command(v=0.5, omega=turn)
            return Command(v=1.5, omega=0.0)


# === HOW TO USE ===
#
# 1. Save this file as your_group_strategy.py
# 2. Modify the MySumoAgent.loop() method with your strategy
# 3. Or use one of the example classes above
# 4. The competition runner will import your agent class
#
# Example competition runner usage:
#
#   from group1_strategy import MySumoAgent as Group1Agent
#   from group2_strategy import MySumoAgent as Group2Agent
#   from sumo_competition import run_competition
#   run_competition(Group1Agent, Group2Agent)