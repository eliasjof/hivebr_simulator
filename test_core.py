"""Test script to verify SimulatorCore works headless."""
import sys
sys.path.insert(0, 'src')

from hivebr.engine.core import SimulatorCore, DEFAULT_CONFIG

def test_basic_simulation():
    print("Creating SimulatorCore...")
    core = SimulatorCore(DEFAULT_CONFIG)
    print(f"  Robots: {core.num_robots}")
    print(f"  World size: {core.world.width}x{core.world.height}")
    print(f"  Robot types: {[r.state().get('type') for r in core.robots]}")
    
    print("\nRunning 10 simulation steps...")
    for i in range(10):
        # Simple forward command for all robots
        commands = {}
        for robot_id in range(core.num_robots):
            robot_type = core.robots[robot_id].state().get("type", "differential")
            if robot_type == "holonomic":
                commands[robot_id] = {"vx": 1.0, "vy": 0.0}
            elif robot_type == "ackermann":
                commands[robot_id] = {"speed": 1.0, "steer": 0.0}
            else:
                commands[robot_id] = {"v": 1.0, "omega": 0.0}
        
        result = core.step(0.03, commands)
        
        # Check first robot state
        state = result.states[0]
        print(f"  Step {i+1}: t={result.sim_time:.3f}, pos=({state.x:.3f}, {state.y:.3f}), theta={state.theta:.3f}")
        
        # Check collisions
        if any(result.collisions):
            print(f"    COLLISIONS: {result.collisions}")
        
        # Check LiDAR
        if result.lidar_readings[0]:
            first_reading = result.lidar_readings[0][0]
            print(f"    LiDAR[0]: angle={first_reading[0]:.3f}, dist={first_reading[1]:.3f}")
    
    print("\nTesting reset...")
    core.reset()
    print(f"  After reset: t={core.sim_time}, collisions={core.collisions}")
    
    print("\nAll tests passed!")
    return True

if __name__ == "__main__":
    test_basic_simulation()