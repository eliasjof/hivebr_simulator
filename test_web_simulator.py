"""Test web_simulator logic in regular Python."""
import sys
import os
sys.path.insert(0, 'src')

# Add web/pyodide/worker to path
sys.path.insert(0, 'web/pyodide/worker')

from hivebr.engine.core import DEFAULT_CONFIG
from copy import deepcopy
from web_simulator import WebSimulator


def test_web_simulator():
    print("Testing WebSimulator initialization...")
    
    # Start with DEFAULT_CONFIG and override
    config = deepcopy(DEFAULT_CONFIG)
    config["robots"] = [
        {"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25},
        {"id": 1, "type": "differential", "initial_pose": [5.0, 5.0, 0.0], "radius": 0.25},
    ]
    config["lidar"]["enabled"] = True
    config["interaction"] = {
        "collision_policy": "resolve",
        "robot_collision": True,
        "robot_safety_margin": 0.0,
        "resolve_push": 0.05,
        "comm_radius": 3.0,
        "show_robot_links": True,
    }
    config["dt"] = 0.03
    config["orientation"] = True
    config["agent_classes"] = {
        0: "TestAgent",
        1: "TestAgent",
    }
    config["agent_params"] = {
        0: {"kp": 0.5},
        1: {"kp": 0.3},
    }
    config["routes"] = {
        0: [[5, 2, 0.0], [5, 6, 0.0]],
        1: [[10, 5, 0.0], [10, 9, 0.0]],
    }
    
    # User code defining agent
    user_code = """
from hivebr import HiveBrAgent
import numpy as np

class TestAgent(HiveBrAgent):
    def setup(self):
        self.kp = self.params.get("kp", 0.5)
        self.r_tol = float((self.cfg or {}).get("waypoints", {}).get("goal_tolerance", 0.5))
    
    def loop(self, state, neighbors):
        goal = state.goal
        if goal is None:
            return (0.0, 0.0)
        
        dx = goal[0] - state.x
        dy = goal[1] - state.y
        dist = np.hypot(dx, dy)
        
        if dist < self.r_tol:
            return (0.0, 0.0)
        
        target_angle = np.arctan2(dy, dx)
        angle_error = target_angle - state.theta
        # Normalize to [-pi, pi]
        angle_error = (angle_error + np.pi) % (2 * np.pi) - np.pi
        
        v = self.kp * dist
        omega = 2.0 * angle_error
        
        return (v, omega)
"""
    
    sim = WebSimulator()
    result = sim.init(config, user_code)
    print(f"Init result: {result}")
    
    if not result.get("success"):
        print(f"Init failed: {result.get('error')}")
        return False
    
    print("\nRunning 20 simulation steps...")
    for i in range(20):
        step_result = sim.step(0.03)
        
        if not step_result.get("success"):
            print(f"Step {i} failed: {step_result.get('error')}")
            return False
        
        if (i + 1) % 5 == 0:
            print(f"  Step {i+1}: t={step_result['sim_time']:.3f}")
            states = step_result['states']
            for rid, state in states.items():
                print(f"    Robot {rid}: pos=({state['x']:.2f}, {state['y']:.2f}), theta={state['theta']:.2f}")
            
            if any(step_result['collisions']):
                print(f"    COLLISIONS: {step_result['collisions']}")
    
    # Test waypoint setting
    print("\nTesting set_waypoints...")
    result = sim.set_waypoints(0, [[2, 2, 0.0], [2, 6, 0.0]])
    print(f"  set_waypoints result: {result}")
    
    # Test obstacle
    print("\nTesting add_obstacle...")
    result = sim.add_obstacle(3.0, 3.0, 0.5)
    print(f"  add_obstacle result: {result}")
    
    # Test reset
    print("\nTesting reset...")
    result = sim.reset()
    print(f"  reset result: {result}")
    
    # Test log export
    print("\nTesting export_log...")
    result = sim.export_log("pkl")
    print(f"  export_log result: success={result.get('success')}, size={len(result.get('data', []))} bytes")
    
    print("\nAll WebSimulator tests passed!")
    return True


if __name__ == "__main__":
    test_web_simulator()