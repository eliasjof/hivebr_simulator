"""
Example: Hexagonal Holonomic Line Follower
3 omni-wheels at 120° + TCRT5000 analog line sensors.

Uses PID control on line error to compute (v, omega) in robot frame,
then inverse kinematics converts to wheel speeds (omega1, omega2, omega3).

Track generation and initial pose setup mirrors line_follower.py.
"""

from pathlib import Path
import sys
import math
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from hivebr.engine import Simulator, load_config

TRACK_PATH = ROOT / "config" / "line_track.png"


# ---------------------------------------------------------------------------
# Track generation (same as line_follower.py)
# ---------------------------------------------------------------------------
def generate_random_track(
    path: Path,
    width_m: float = 4.0,
    height_m: float = 3.0,
    resolution: float = 0.005,
    line_width_m: float = 0.02,
    seed: int = 7,
):
    """Creates a random closed track and saves as black line on white background.

    Returns centerline points in world coordinates (meters).
    """
    path = Path(path)
    rng = np.random.default_rng(seed)
    width_px = int(round(width_m / resolution))
    height_px = int(round(height_m / resolution))

    t = np.linspace(0.0, 2.0 * np.pi, 2000, endpoint=False)
    radius = np.ones_like(t)
    for k in (2, 3, 4):
        amplitude = rng.uniform(0.03, 0.08) / k
        phase = rng.uniform(0.0, 2.0 * np.pi)
        radius += amplitude * np.cos(k * t + phase)
    radius = np.clip(radius, 0.75, 1.05)

    cx, cy = width_m / 2.0, height_m / 2.0
    rx, ry = width_m * 0.36, height_m * 0.36
    xs = cx + rx * radius * np.cos(t)
    ys = cy + ry * radius * np.sin(t)

    image = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    line_px = max(1, int(round(line_width_m / resolution)))
    points_px = [
        (x / resolution, (height_px - 1) - y / resolution)
        for x, y in zip(xs, ys)
    ]
    draw.line(points_px + [points_px[0]], fill=(0, 0, 0), width=line_px, joint="curve")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)

    return np.column_stack([xs, ys])


def pose_on_track(points: np.ndarray, index: int = 0, lookahead: int = 12):
    """Returns ``(x, y, theta)`` on the track, aligned to tangent."""
    n = len(points)
    p0 = points[index % n]
    p1 = points[(index + lookahead) % n]
    theta = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    return float(p0[0]), float(p0[1]), float(theta)


def line_follower_controller(robot, world, goal, config, dt, lidar_readings):
    """
    PID line following controller for hexagonal holonomic robot.
    
    Reads line sensors, computes line error, then uses PID to determine
    robot velocity (v, omega) in robot frame. Converts to world frame
    (vx, vy, omega) for inverse kinematics.
    """
    # Read line sensors
    robot.read_line_sensors(world.line_map)
    
    # If finished, stop
    if robot.finished:
        return {"v": 0.0, "omega": 0.0}
    
    # If line lost, try to recover (spin in place)
    if robot.line_lost:
        # Spin to search for line
        return {"v": 0.0, "omega": 2.0 * robot._last_sign}
    
    # Get PID gains from config
    pid = config.get("line_pid", {})
    base_speed = pid.get("base_speed", 0.3)
    kp = pid.get("kp", 4.0)
    ki = pid.get("ki", 0.05)
    kd = pid.get("kd", 0.9)
    integral_limit = pid.get("integral_limit", 1.0)
    
    # Line error: -1 (line right) to +1 (line left)
    error = robot.line_error
    
    # PID computation (simple version)
    if not hasattr(robot, '_line_integral'):
        robot._line_integral = 0.0
        robot._line_last_error = 0.0
    
    robot._line_integral += error * dt
    robot._line_integral = max(-integral_limit, min(integral_limit, robot._line_integral))
    derivative = (error - robot._line_last_error) / dt if dt > 0 else 0.0
    robot._line_last_error = error
    
    omega_cmd = kp * error + ki * robot._line_integral + kd * derivative
    v_cmd = base_speed
    
    # Clamp to robot limits
    v_cmd = max(-robot.max_speed, min(robot.max_speed, v_cmd))
    omega_cmd = max(-robot.max_omega, min(robot.max_omega, omega_cmd))
    
    # Return in robot frame (v forward, omega angular)
    return {"v": v_cmd, "omega": omega_cmd}


def draw_info(sim, screen):
    """Draw robot state info on screen."""
    import pygame
    font = pygame.font.SysFont("consolas", 14)
    robot = sim.robot
    
    lines = [
        "Hexagonal Holonomic Line Follower",
        "",
        f"Pos:  x={robot.x:6.2f}  y={robot.y:6.2f}  th={math.degrees(robot.theta):6.1f}°",
        f"Vel:  vx={robot.vx:6.2f}  vy={robot.vy:6.2f}  w={robot.omega:6.2f}",
        f"Servo: w1={robot.omega1:6.2f}  w2={robot.omega2:6.2f}  w3={robot.omega3:6.2f} rad/s",
        "",
        f"Line: error={robot.line_error:6.3f}  pos={robot.line_position:6.3f}m  lost={robot.line_lost}",
        f"Sensors: " + "  ".join(f"{r:.2f}" for r in robot.sensor_readings),
        "",
        f"Laps: {len(robot.lap_times)}  Time: {robot.time:.2f}s",
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
    import argparse

    parser = argparse.ArgumentParser(description="Hexagonal Holonomic Line Follower (PID)")
    parser.add_argument("--seed", type=int, default=7, help="track seed")
    parser.add_argument("--sensors", type=int, default=None, help="number of sensors (2, 5 or 8)")
    parser.add_argument("--regenerate", action="store_true", help="force new track")
    args = parser.parse_args()

    config = load_config(ROOT / "config" / "hexagonal_holonomic_line_follower.yaml")

    if args.sensors is not None:
        config["robot"]["num_sensors"] = int(args.sensors)

    if args.regenerate or not TRACK_PATH.exists():
        print(f"Generating random track (seed={args.seed}) -> {TRACK_PATH}")
    points = generate_random_track(TRACK_PATH, seed=args.seed)

    config["world"]["line_map_image"] = str(TRACK_PATH)

    sim = Simulator(config=config, controller=line_follower_controller, draw_callback=draw_info)

    # Initialize robot on track
    x0, y0, theta0 = pose_on_track(points)
    sim.robot.set_initial_pose(x0, y0, theta0)
    sim.camera.initial_zoom = 1.0
    sim.camera.reset()

    print("=" * 60)
    print("Hexagonal Holonomic Line Follower")
    print("=" * 60)
    print(f"Controller: PID on line error -> (v, omega) -> inverse kinematics")
    print(f"Robot: 3 omni-wheels + TCRT5000 sensor array ({sim.robot.num_sensors} sensors)")
    print(f"Initial pose: ({x0:.2f}, {y0:.2f}, {math.degrees(theta0):.1f}°)")
    print(f"PID: kp={config['line_pid']['kp']}, ki={config['line_pid']['ki']}, kd={config['line_pid']['kd']}")
    print("SPACE - Pause/Resume | Click - Set waypoint")
    print("=" * 60)

    sim.run()

    stats = sim.robot.lap_statistics()
    if stats["count"]:
        print(
            f"\nLap summary: {stats['count']} lap(s) | "
            f"mean={stats['mean']:.2f}s | best={stats['best']:.2f}s | "
            f"worst={stats['worst']:.2f}s"
        )
        print("Lap times (s):", [f"{t:.2f}" for t in sim.robot.lap_times])
    elif getattr(sim.robot, "finished", False):
        print(f"\nTrack completed in {sim.robot.finish_time:.2f}s.")
    else:
        print("\nSimulation ended without complete laps.")