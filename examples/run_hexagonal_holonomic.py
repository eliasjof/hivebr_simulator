"""
Example: Hexagonal Holonomic Robot (3 wheels at 120 degrees)

Direct servo control using inverse kinematics with control allocation.
Uses world-frame velocity (vx, vy) for goal tracking and omega for alignment,
then converts to wheel speeds (omega1, omega2, omega3) via inverse kinematics.

Kinematics:
    [ẋ]   [ -r/√3   0     r/√3  ] [ω1]
    [ẏ] = [  r/3   -2r/3   r/3  ] [ω2]
    [θ̇]   [ r/3L   r/3L   r/3L  ] [ω3]

Wheel geometry (matching kinematic matrix):
    Wheel 1: 60°  (right-upper side)  - tangent 150°
    Wheel 2: 180° (left side / back)  - tangent 270°
    Wheel 3: 300° (right-lower side)  - tangent 30°
"""

from pathlib import Path
import sys
import math
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hivebr.engine import Simulator, load_config


def servo_controller(robot, world, goal, config, dt, lidar_readings):
    """
    Direct servo control using inverse kinematics with control allocation.
    Uses world-frame velocity control (vx, vy) for natural goal tracking,
    then converts to wheel speeds (omega1, omega2, omega3) via inverse kinematics.
    Implements control allocation to handle wheel saturation.
    """
    if goal is None:
        return {"omega1": 0.0, "omega2": 0.0, "omega3": 0.0}
    
    # Goal position
    goal_pos = np.array(goal[:2])
    pos = robot.position
    to_goal = goal_pos - pos
    dist = np.linalg.norm(to_goal)
    
    # Goal tolerance
    tolerance = 0.15
    if dist < tolerance:
        return {"omega1": 0.0, "omega2": 0.0, "omega3": 0.0}
    
    # World-frame velocity control (proportional to position error)
    kv = 2.0
    vx_des = kv * to_goal[0]
    vy_des = kv * to_goal[1]
    
    # Limit linear speed
    speed = math.hypot(vx_des, vy_des)
    if speed > robot.max_speed:
        scale = robot.max_speed / speed
        vx_des *= scale
        vy_des *= scale
    
    # Angular velocity to align with goal direction
    goal_angle = math.atan2(to_goal[1], to_goal[0])
    angle_diff = (goal_angle - robot.theta + math.pi) % (2 * math.pi) - math.pi
    kw = 3.0
    omega_des = kw * angle_diff
    omega_des = max(-robot.max_omega, min(robot.max_omega, omega_des))
    
    # Control allocation: scale down (vx, vy, omega) until wheels fit within limits
    max_servo = robot.servo_max_speed
    
    for _ in range(5):
        omega1, omega2, omega3 = robot._inverse_kinematics(vx_des, vy_des, omega_des)
        max_wheel = max(abs(omega1), abs(omega2), abs(omega3))
        if max_wheel <= max_servo:
            break
        scale = max_servo / max_wheel
        vx_des *= scale
        vy_des *= scale
        omega_des *= scale
    
    # Final inverse kinematics
    omega1, omega2, omega3 = robot._inverse_kinematics(vx_des, vy_des, omega_des)
    
    # Final clamp
    omega1 = max(-max_servo, min(max_servo, omega1))
    omega2 = max(-max_servo, min(max_servo, omega2))
    omega3 = max(-max_servo, min(max_servo, omega3))
    
    return {"omega1": omega1, "omega2": omega2, "omega3": omega3}


def draw_info(sim, screen):
    """Draw robot state info on screen."""
    import pygame
    font = pygame.font.SysFont("consolas", 14)
    robot = sim.robot
    
    lines = [
        "Hexagonal Holonomic Robot - Servo Control",
        "",
        f"Pos:  x={robot.x:6.2f}  y={robot.y:6.2f}  th={robot.theta:6.2f}",
        f"Vel:  vx={robot.vx:6.2f}  vy={robot.vy:6.2f}  w={robot.omega:6.2f}",
        f"Servo: w1={robot.omega1:6.2f}  w2={robot.omega2:6.2f}  w3={robot.omega3:6.2f} rad/s",
        "",
        f"Goal: {sim.waypoints.get_current_waypoint()}",
        f"Waypoint: {sim.waypoints.current_index + 1}/{len(sim.waypoints.waypoints)}",
        "",
        "SPACE - Pause/Resume",
        "Click - Set waypoint",
    ]
    
    y = 20
    for line in lines:
        surf = font.render(line, True, (255, 255, 255))
        screen.blit(surf, (20, y))
        y += 20


if __name__ == "__main__":
    config = load_config(ROOT / "config" / "hexagonal_holonomic.yaml")
    
    sim = Simulator(config=config, controller=servo_controller, draw_callback=None)
    sim.running_simulation = sim.config.get("running_simulation", False)
    
    print("=" * 50)
    print("Hexagonal Holonomic Robot - Servo Control Demo")
    print("=" * 50)
    print("Controller: Direct wheel speeds (omega1, omega2, omega3)")
    print("Using inverse kinematics + control allocation")
    print("SPACE - Pause/Resume | Click - Set waypoint")
    print("=" * 50)
    
    sim.run()