"""Test script to verify WebSimulator reaches waypoints."""
import sys
sys.path.insert(0, 'src')

from hivebr.engine.core import DEFAULT_CONFIG
from web.pyodide.web_simulator import WebSimulator
import numpy as np

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

config["routes"] = {0: [[5, 2, 0.0], [5, 6, 0.0], [2, 6, 0.0], [2, 2, 0.0]]}
config["agent_classes"] = {0: "PatrolAgent"}

sim = WebSimulator()
result = sim.init(config, """
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
""")

if not result.get("success"):
    print(f"Init failed: {result.get('error')}")
    sys.exit(1)

print("Running simulation for 200 steps...")
waypoints_reached = 0
prev_waypoint_idx = -1

for i in range(200):
    step_result = sim.step(0.03)
    if not step_result.get("success"):
        print(f"Step {i} failed: {step_result.get('error')}")
        sys.exit(1)
    
    state = step_result["states"]["0"]
    current_waypoint = sim.core.waypoint_managers[0].current_index
    
    if current_waypoint != prev_waypoint_idx:
        waypoints_reached += 1
        print(f"Waypoint {current_waypoint} reached! Total: {waypoints_reached}")
        prev_waypoint_idx = current_waypoint
    
    if i % 40 == 0:
        print(f"Step {i}: t={step_result['sim_time']:.2f}, pos=({state['x']:.2f}, {state['y']:.2f}), theta={state['theta']:.2f}, wp={current_waypoint}")

print(f"\nTotal waypoints reached: {waypoints_reached}")
print("Test completed!")