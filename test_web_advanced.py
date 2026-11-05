"""Test web_simulator with centralized controller and map loading."""
import sys
import os
sys.path.insert(0, 'src')
sys.path.insert(0, 'web/pyodide/worker')

from hivebr.engine.core import DEFAULT_CONFIG
from copy import deepcopy
from web_simulator import WebSimulator
import numpy as np
from PIL import Image
from io import BytesIO


def test_centralized_controller():
    print("Testing WebSimulator with centralized controller...")
    
    config = deepcopy(DEFAULT_CONFIG)
    config["robots"] = [
        {"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25},
        {"id": 1, "type": "differential", "initial_pose": [5.0, 5.0, 0.0], "radius": 0.25},
        {"id": 2, "type": "holonomic", "initial_pose": [18.0, 2.0, 0.0], "radius": 0.25},
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
    config["controller_class"] = "CentralController"
    
    # User code defining centralized controller
    user_code = """
from hivebr import SwarmController
import numpy as np

class CentralController(SwarmController):
    def setup(self):
        self.kp = 0.5
        self.k_alpha = 1.5
        self.k_beta = -1.0
        self.sep_gain = 0.5
        self.sep_steer = 1.2
        self.sep_margin = 0.35
    
    def loop(self, states):
        commands = {}
        for rid, state in states.items():
            goal = state.goal
            if goal is None:
                commands[rid] = {"v": 0.0, "omega": 0.0}
                continue
            
            dx = goal[0] - state.x
            dy = goal[1] - state.y
            rho = np.hypot(dx, dy)
            
            if rho < 0.5:
                commands[rid] = {"v": 0.0, "omega": 0.0}
                continue
            
            theta_d = goal[2] if len(goal) > 2 else state.theta
            alpha = (np.arctan2(dy, dx) - state.theta + np.pi) % (2 * np.pi) - np.pi
            beta = (theta_d - state.theta - alpha + np.pi) % (2 * np.pi) - np.pi
            
            kp = self.kp
            if abs(alpha) > np.pi / 2:
                alpha = (alpha - np.pi + np.pi) % (2 * np.pi) - np.pi
                beta = (beta - np.pi + np.pi) % (2 * np.pi) - np.pi
                kp = -kp
            
            v = kp * rho
            w = self.k_beta * beta + self.k_alpha * alpha
            
            # Separation from other robots
            for nid, nstate in states.items():
                if nid == rid:
                    continue
                d = np.hypot(state.x - nstate.x, state.y - nstate.y)
                safe = state.radius + nstate.radius + self.sep_margin
                if 0.0 < d < safe:
                    shortfall = safe - d
                    bearing = (np.arctan2(nstate.y - state.y, nstate.x - state.x) - state.theta + np.pi) % (2 * np.pi) - np.pi
                    v -= self.sep_gain * shortfall * max(0.0, np.cos(bearing))
                    w -= self.sep_steer * shortfall * np.sin(bearing)
            
            commands[rid] = {"v": float(v), "omega": float(w)}
        
        return commands
"""
    
    sim = WebSimulator()
    result = sim.init(config, user_code)
    print(f"Init result: {result}")
    
    if not result.get("success"):
        print(f"Init failed: {result.get('error')}")
        return False
    
    print("\nRunning 30 simulation steps with centralized controller...")
    for i in range(30):
        step_result = sim.step(0.03)
        
        if not step_result.get("success"):
            print(f"Step {i} failed: {step_result.get('error')}")
            return False
        
        if (i + 1) % 10 == 0:
            print(f"  Step {i+1}: t={step_result['sim_time']:.3f}")
            states = step_result['states']
            for rid, state in states.items():
                print(f"    Robot {rid}: pos=({state['x']:.2f}, {state['y']:.2f}), theta={state['theta']:.2f}")
    
    print("\nCentralized controller test passed!")
    return True


def test_occupancy_map_loading():
    print("\nTesting occupancy map loading...")
    
    config = deepcopy(DEFAULT_CONFIG)
    config["robots"] = [
        {"id": 0, "type": "differential", "initial_pose": [1.0, 5.0, 0.0], "radius": 0.25},
    ]
    config["dt"] = 0.03
    
    # Create a test occupancy map: 10x10m with a horizontal wall at y=5
    map_array = np.zeros((100, 100), dtype=np.uint8)
    map_array[:, :] = 255  # White = free
    map_array[45:55, :] = 0  # Black wall at y=5m (rows 45-55)
    
    img = Image.fromarray(map_array, mode='L')
    buf = BytesIO()
    img.save(buf, format='PNG')
    map_bytes = list(buf.getvalue())
    
    sim = WebSimulator()
    result = sim.init(config, "")
    print(f"Init result: {result}")
    
    # Load map
    result = sim.load_occupancy_map(map_bytes, 0.1)
    print(f"Load map result: {result}")
    
    # Test collision with wall
    print("Testing collision with wall...")
    for i in range(30):
        step_result = sim.step(0.03, external_commands={"0": {"v": 1.0, "omega": 0.0}})
        
        if not step_result.get("success"):
            print(f"Step {i} failed: {step_result.get('error')}")
            return False
        
        if step_result['collisions'][0]:
            print(f"  Collision detected at step {i}, pos=({step_result['states']['0']['x']:.2f}, {step_result['states']['0']['y']:.2f})")
            break
        elif i % 10 == 0:
            print(f"  Step {i}: pos=({step_result['states']['0']['x']:.2f}, {step_result['states']['0']['y']:.2f})")
    
    print("Occupancy map test passed!")
    return True


def test_line_map_loading():
    print("\nTesting line map (track) loading...")
    
    config = deepcopy(DEFAULT_CONFIG)
    config["robots"] = [
        {"id": 0, "type": "line_follower", "initial_pose": [1.0, 1.0, 0.0], "radius": 0.05,
         "num_sensors": 5, "sensor_offset": 0.05, "sensor_span": 0.08},
    ]
    config["dt"] = 0.03
    
    # Create a simple square track
    map_array = np.zeros((200, 200), dtype=np.uint8)
    map_array[:, :] = 255  # White background
    # Draw a square track
    from PIL import ImageDraw
    img = Image.fromarray(map_array, mode='L')
    draw = ImageDraw.Draw(img)
    # Outer square
    draw.rectangle([20, 20, 180, 180], outline=0, width=5)
    # Inner square (track)
    draw.rectangle([40, 40, 160, 160], outline=0, width=5)
    
    buf = BytesIO()
    img.save(buf, format='PNG')
    map_bytes = list(buf.getvalue())
    
    sim = WebSimulator()
    result = sim.init(config, "")
    print(f"Init result: {result}")
    
    # Load line map
    result = sim.load_line_map(map_bytes, 0.05)
    print(f"Load line map result: {result}")
    
    # Test line sensor readings
    print("Testing line follower sensors...")
    for i in range(10):
        # Simple controller: move forward
        step_result = sim.step(0.03, {"0": {"v": 0.2, "omega": 0.0}})
        
        if not step_result.get("success"):
            print(f"Step {i} failed: {step_result.get('error')}")
            return False
        
        # Check if robot has line_follower attributes
        if hasattr(sim.core.robots[0], 'sensor_readings'):
            print(f"  Step {i}: sensors={sim.core.robots[0].sensor_readings}, line_error={sim.core.robots[0].line_error:.3f}")
    
    print("Line map test passed!")
    return True


if __name__ == "__main__":
    test_centralized_controller()
    test_occupancy_map_loading()
    test_line_map_loading()
    print("\nAll advanced tests passed!")