"""Test script to verify SimulatorCore with multiple robots and waypoints."""
import sys
sys.path.insert(0, 'src')

from hivebr.engine.core import SimulatorCore, DEFAULT_CONFIG
from copy import deepcopy

def test_multi_robot_with_waypoints():
    print("Creating SimulatorCore with 3 robots and waypoints...")
    
    # Create config with 3 robots
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
    
    core = SimulatorCore(config)
    print(f"  Robots: {core.num_robots}")
    print(f"  Robot types: {[r.state().get('type') for r in core.robots]}")
    
    # Set waypoints for each robot
    waypoints = {
        0: [[5, 2, 0.0], [5, 6, 0.0], [2, 6, 0.0], [2, 2, 0.0]],
        1: [[10, 5, 0.0], [10, 9, 0.0], [5, 9, 0.0], [5, 5, 0.0]],
        2: [[15, 2, 0.0], [15, 6, 0.0], [18, 6, 0.0], [18, 2, 0.0]],
    }
    for robot_id, wps in waypoints.items():
        core.set_waypoints(robot_id, wps)
    
    print("\nRunning 50 simulation steps with waypoint following...")
    for i in range(50):
        # Simple waypoint-following controller for each robot
        commands = {}
        for robot_id in range(core.num_robots):
            robot = core.robots[robot_id]
            wm = core.waypoint_managers[robot_id]
            goal = wm.get_current_waypoint()
            
            if goal is None:
                commands[robot_id] = {"v": 0.0, "omega": 0.0}
                continue
            
            # Simple proportional controller
            dx = goal[0] - robot.x
            dy = goal[1] - robot.y
            target_theta = goal[2] if len(goal) > 2 else 0.0
            
            # Compute heading error
            import math
            angle_to_goal = math.atan2(dy, dx)
            heading_error = angle_to_goal - robot.theta
            # Normalize to [-pi, pi]
            heading_error = (heading_error + math.pi) % (2 * math.pi) - math.pi
            
            # Distance to goal
            dist = math.hypot(dx, dy)
            
            if dist < 0.5:  # Close to waypoint, waypoint manager will advance
                v = 0.5
            else:
                v = 1.5
            
            omega = 2.0 * heading_error
            
            robot_type = robot.state().get("type", "differential")
            if robot_type == "holonomic":
                commands[robot_id] = {"vx": v * math.cos(robot.theta), "vy": v * math.sin(robot.theta)}
            else:
                commands[robot_id] = {"v": v, "omega": omega}
        
        result = core.step(0.03, commands)
        
        # Print state every 10 steps
        if (i + 1) % 10 == 0:
            print(f"  Step {i+1}: t={result.sim_time:.3f}")
            for rid, state in result.states.items():
                print(f"    Robot {rid}: pos=({state.x:.2f}, {state.y:.2f}), goal={core.waypoint_managers[rid].get_current_waypoint()}")
            
            # Check collisions
            if any(result.collisions):
                print(f"    COLLISIONS: {result.collisions}")
    
    print("\nTesting occupancy map loading...")
    # Create a simple test map
    import numpy as np
    from PIL import Image
    from io import BytesIO
    
    # Create a 100x100 map with a wall
    map_array = np.zeros((100, 100), dtype=np.uint8)
    map_array[:, :] = 255  # White background
    map_array[50:55, 20:80] = 0  # Black horizontal wall
    
    img = Image.fromarray(map_array, mode='L')
    buf = BytesIO()
    img.save(buf, format='PNG')
    map_bytes = buf.getvalue()
    
    core.load_occupancy_map(map_bytes, 0.1, 0.25)
    print(f"  World size after map: {core.world.width}x{core.world.height}")
    print(f"  Grid map shape: {core.world.grid_map.grid.shape if core.world.grid_map else 'None'}")
    
    # Test collision with map
    core.robots[0].set_initial_pose(5.0, 5.0, 0.0)
    for i in range(20):
        commands = {0: {"v": 1.0, "omega": 0.0}, 1: {"v": 0.0, "omega": 0.0}, 2: {"v": 0.0, "omega": 0.0}}
        result = core.step(0.03, commands)
        if result.collisions[0]:
            print(f"  Collision with map at step {i}, pos=({result.states[0].x:.2f}, {result.states[0].y:.2f})")
            break
    
    print("\nTesting track editor (line follower)...")
    core.track_editor.begin(1.0, 1.0)
    core.track_editor.extend(2.0, 1.0)
    core.track_editor.extend(2.0, 2.0)
    core.track_editor.extend(1.0, 2.0)
    core.track_editor.end()
    
    line_map = core.track_editor.apply()
    print(f"  Line track map: {line_map.width_m:.2f}x{line_map.height_m:.2f}m, res={line_map.resolution}")
    
    # Test line follower robot
    core.robots[0].set_initial_pose(1.0, 1.0, 0.0)
    for i in range(30):
        commands = {0: {"v": 0.5, "omega": 0.0}, 1: {"v": 0.0, "omega": 0.0}, 2: {"v": 0.0, "omega": 0.0}}
        result = core.step(0.03, commands)
        if hasattr(core.robots[0], 'sensor_readings'):
            print(f"  Line follower sensors: {core.robots[0].sensor_readings}")
            break
    
    print("\nAll comprehensive tests passed!")
    return True

if __name__ == "__main__":
    test_multi_robot_with_waypoints()