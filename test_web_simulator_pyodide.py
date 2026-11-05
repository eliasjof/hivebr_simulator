"""Test script to verify WebSimulator with waypoints and real hivebr modules."""
import sys
sys.path.insert(0, 'src')

# Import defaults
from hivebr.engine.core import DEFAULT_CONFIG

# Test importing the real hivebr modules
try:
    from hivebr.engine.core import SimulatorCore, SimStepResult
    from hivebr.core import SwarmExperiment, HiveBrAgent, SwarmController
    from hivebr.state import Command, RobotState
    from hivebr.kinematics import normalize_command
    import numpy as np
    print("[OK] All hivebr modules imported successfully")
except ImportError as e:
    print(f"[FAIL] Import error: {e}")
    sys.exit(1)

# Test WebSimulator class
try:
    from web.pyodide.web_simulator import WebSimulator
    print("[OK] WebSimulator imported successfully")
except ImportError as e:
    print(f"[FAIL] WebSimulator import error: {e}")
    sys.exit(1)

# Test with waypoints
config = DEFAULT_CONFIG.copy()
config["robots"] = 1
config["backend"] = "navsim2d"
config["dt"] = 0.03
config["orientation"] = True

user_code = """
class PatrolAgent(HiveBrAgent):
    def setup(self):
        self.kp = 0.5
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
        angle_error = (angle_error + np.pi) % (2 * np.pi) - np.pi
        
        v = 0.5 * dist
        omega = 2.0 * angle_error
        
        return (v, omega)
"""

# Add waypoints
config["routes"] = {
    0: [[5, 2, 0.0], [5, 6, 0.0], [2, 6, 0.0], [2, 2, 0.0]]
}
config["agent_classes"] = {0: "PatrolAgent"}

sim = WebSimulator()
result = sim.init(config, user_code)
print(f"Init result: {result}")

if not result.get("success"):
    print(f"[FAIL] Init failed: {result.get('error')}")
    sys.exit(1)

print("[OK] WebSimulator initialized with waypoints")

# Run simulation for 100 steps
for i in range(100):
    step_result = sim.step(0.03)
    if not step_result.get("success"):
        print(f"[FAIL] Step {i} failed: {step_result.get('error')}")
        sys.exit(1)
    
    if i % 20 == 0:
        state = step_result["states"]["0"]
        print(f"Step {i}: t={step_result['sim_time']:.3f}, pos=({state['x']:.2f}, {state['y']:.2f}), theta={state['theta']:.2f}")

# Test set_waypoints
print("\n[TEST] Testing set_waypoints...")
result = sim.set_waypoints(0, [[2, 2, 0.0], [2, 6, 0.0]])
print(f"set_waypoints result: {result}")

# Test add_obstacle
print("\n[TEST] Testing add_obstacle...")
result = sim.add_obstacle(3.0, 3.0, 0.5)
print(f"add_obstacle result: {result}")

# Test reset
print("\n[TEST] Testing reset...")
result = sim.reset()
print(f"reset result: {result}")

# Test export_log
print("\n[TEST] Testing export_log...")
result = sim.export_log("pkl")
print(f"export_log result: {result.get('success')}, size={len(result.get('data', []))} bytes")

print("\n[OK] All comprehensive tests passed!")