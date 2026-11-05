"""
Quick test to verify sumo agent logic without GUI.
"""

import math
from hivebr.state import RobotState
from sumo_competition import AggressiveSumoAgent, DefensiveSumoAgent, SumoConfig

def test_agent_logic():
    """Test that agents produce valid commands."""
    config = SumoConfig()
    
    # Create agents
    agent1 = AggressiveSumoAgent(robot_id=0, config={})
    agent2 = DefensiveSumoAgent(robot_id=1, config={})
    
    agent1.set_opponent(1)
    agent2.set_opponent(0)
    
    # Test states - NEW SETUP: on Y-axis facing each other
    state1 = RobotState(id=0, x=0.0, y=0.45, theta=-math.pi/2, v=0.0, omega=0.0, radius=0.10)  # Top, facing down
    state2 = RobotState(id=1, x=0.0, y=-0.45, theta=math.pi/2, v=0.0, omega=0.0, radius=0.10)   # Bottom, facing up
    
    neighbors1 = {1: state2}
    neighbors2 = {0: state1}
    
    # Test loop
    cmd1 = agent1.loop(state1, neighbors1)
    cmd2 = agent2.loop(state2, neighbors2)
    
    print("Agent 1 (Aggressive) command:", cmd1)
    print("Agent 2 (Defensive) command:", cmd2)
    
    # Verify commands are valid
    assert isinstance(cmd1.v, float), "v should be float"
    assert isinstance(cmd1.omega, float), "omega should be float"
    assert abs(cmd1.v) <= config.max_speed, "v exceeds max_speed"
    assert abs(cmd1.omega) <= config.max_omega, "omega exceeds max_omega"
    
    assert isinstance(cmd2.v, float), "v should be float"
    assert isinstance(cmd2.omega, float), "omega should be float"
    assert abs(cmd2.v) <= config.max_speed, "v exceeds max_speed"
    assert abs(cmd2.omega) <= config.max_omega, "omega exceeds max_omega"
    
    print("\n[OK] All agent logic tests passed!")
    
    # Test ring boundary check
    assert agent1.is_in_ring(0.0, 0.0) == True, "Center should be in ring"
    assert agent1.is_in_ring(0.77, 0.0) == False, "Edge should be out of ring"
    assert agent1.is_in_ring(0.6, 0.0) == True, "Inside should be in ring"
    print("[OK] Ring boundary checks passed!")
    
    # Test angle calculations
    angle = agent1.angle_to_opponent(state1, neighbors1)
    print(f"Angle to opponent: {angle:.3f} rad ({math.degrees(angle):.1f} deg)")
    
    dist = agent1.distance_to_opponent(state1, neighbors1)
    print(f"Distance to opponent: {dist:.3f} m")
    
    print("\n[OK] All tests passed!")

if __name__ == "__main__":
    test_agent_logic()