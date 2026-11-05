"""Headless test of the referee logic (no GUI)."""

import time
import math
from typing import Dict
from sumo_referee import (
    SumoReferee, TournamentConfig, TeamInfo, RobotCompetitionState,
    MatchStatus, RobotStatus, RobotState, CompetitionAgent, Command
)
from hivebr.state import RobotState as HiveRobotState


class DummyAgent(CompetitionAgent):
    """Simple agent for testing."""
    def __init__(self, robot_id=None, config=None, **params):
        super().__init__(robot_id, config, **params)
        self.team_name = "Dummy"
        self.target_x = 0.0
        self.target_y = 0.0
    
    def set_target(self, x, y):
        self.target_x = x
        self.target_y = y
    
    def loop(self, state: RobotState, neighbors: Dict[int, RobotState]) -> Command:
        if not self.is_in_ring(state.x, state.y):
            return Command(v=0.0, omega=0.0)
        
        angle = self.angle_to_target(state, self.target_x, self.target_y)
        if abs(angle) > 0.2:
            turn = self.max_omega if angle > 0 else -self.max_omega
            return Command(v=0.5, omega=turn)
        return Command(v=2.0, omega=0.0)


def test_referee_basic():
    """Test referee detection logic."""
    print("Testing SumoReferee...")
    
    config = TournamentConfig(
        match_duration=10.0,
        ring_radius=0.77,
        robot_radius=0.10,
        border_width=0.05
    )
    
    referee = SumoReferee(config)
    
    # Register teams
    team1 = TeamInfo("team1", "Time Azul", DummyAgent, (30, 144, 255))
    team2 = TeamInfo("team2", "Time Vermelho", DummyAgent, (220, 20, 60))
    
    referee.register_team(0, team1)
    referee.register_team(1, team2)
    referee.start_match("test_001")
    
    print(f"Match started: {referee.match_id}")
    print(f"Effective radius: {referee.effective_radius:.3f}m")
    
    # Simulate robots moving
    # Robot 0 starts at (0, 0.45) facing down, moves toward center
    # Robot 1 starts at (0, -0.45) facing up, moves toward center
    
    # Test 1: Both in ring
    robot_states = {
        0: HiveRobotState(id=0, x=0.0, y=0.3, theta=-math.pi/2, v=1.0, omega=0.0, radius=0.10),
        1: HiveRobotState(id=1, x=0.0, y=-0.3, theta=math.pi/2, v=1.0, omega=0.0, radius=0.10),
    }
    
    result = referee.update(robot_states, 0.03)
    print(f"Test 1 - Both in ring: {referee.get_status_text()} | Result: {result}")
    
    # Test 2: Robot 1 pushed out
    robot_states = {
        0: HiveRobotState(id=0, x=0.0, y=0.0, theta=-math.pi/2, v=0.0, omega=0.0, radius=0.10),
        1: HiveRobotState(id=1, x=0.0, y=0.8, theta=math.pi/2, v=0.0, omega=0.0, radius=0.10),  # Outside!
    }
    
    result = referee.update(robot_states, 0.03)
    print(f"Test 2 - Robot 1 out: {referee.get_status_text()} | Result: {result}")
    
    if result:
        print(f"  Winner: {referee.team_info[result.winner_team_id].name}")
        print(f"  Reason: {result.reason}")
        print(f"  Duration: {result.duration:.2f}s")
    
    print("\n[OK] Referee tests passed!")


def test_edge_detection():
    """Test edge distance calculations."""
    print("\nTesting edge detection...")
    
    config = TournamentConfig()
    agent = DummyAgent(config={"sumo": {"ring_radius": 0.77, "robot_radius": 0.10, "border_width": 0.05},
                               "robot": {"max_speed": 3.0, "max_omega": 6.0}})
    
    # At center
    state = HiveRobotState(id=0, x=0.0, y=0.0, theta=0.0, v=0.0, omega=0.0, radius=0.10)
    assert abs(agent.distance_to_center(state) - 0.0) < 0.01
    assert abs(agent.distance_to_edge(state) - 0.62) < 0.01  # 0.77 - 0.10 - 0.05
    assert agent.is_in_ring(0.0, 0.0) == True
    
    # Near edge
    state = HiveRobotState(id=0, x=0.6, y=0.0, theta=0.0, v=0.0, omega=0.0, radius=0.10)
    assert abs(agent.distance_to_center(state) - 0.6) < 0.01
    assert abs(agent.distance_to_edge(state) - 0.02) < 0.01
    assert agent.is_in_ring(0.6, 0.0) == True
    
    # Outside
    state = HiveRobotState(id=0, x=0.7, y=0.0, theta=0.0, v=0.0, omega=0.0, radius=0.10)
    assert agent.is_in_ring(0.7, 0.0) == False
    
    print("[OK] Edge detection tests passed!")


def test_angle_calculations():
    """Test angle calculations."""
    print("\nTesting angle calculations...")
    
    config = TournamentConfig()
    agent = DummyAgent(config={"sumo": {"ring_radius": 0.77, "robot_radius": 0.10, "border_width": 0.05},
                               "robot": {"max_speed": 3.0, "max_omega": 6.0}})
    agent.set_opponent(1)
    
    # Robot at (0, 0.3) facing down (-pi/2), opponent at (0, -0.3)
    state = HiveRobotState(id=0, x=0.0, y=0.3, theta=-math.pi/2, v=0.0, omega=0.0, radius=0.10)
    opp_state = HiveRobotState(id=1, x=0.0, y=-0.3, theta=math.pi/2, v=0.0, omega=0.0, radius=0.10)
    neighbors = {1: opp_state}
    
    angle = agent.angle_to_opponent(state, neighbors)
    # Opponent is straight ahead (same direction robot is facing)
    # angle should be ~0
    print(f"  Angle to opponent (straight ahead): {math.degrees(angle):.1f}°")
    assert abs(angle) < 0.1
    
    # Robot facing up, opponent down
    state = HiveRobotState(id=0, x=0.0, y=0.3, theta=math.pi/2, v=0.0, omega=0.0, radius=0.10)
    angle = agent.angle_to_opponent(state, neighbors)
    # Opponent is behind (180 degrees)
    print(f"  Angle to opponent (behind): {math.degrees(angle):.1f}°")
    assert abs(abs(angle) - math.pi) < 0.1
    
    print("[OK] Angle calculation tests passed!")


if __name__ == "__main__":
    test_referee_basic()
    test_edge_detection()
    test_angle_calculations()
    print("\n" + "="*50)
    print("ALL TESTS PASSED!")
    print("="*50)