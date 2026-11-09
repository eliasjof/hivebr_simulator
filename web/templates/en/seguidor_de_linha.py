"""Line follower with differential robot and analog TCRT5000 sensors.

The script:
  1. Generates a random closed track and saves it as an image (black line
     2 cm wide on white background) in ``config/line_track.png``.
  2. Loads ``config/line_follower.yaml``.
  3. Positions the robot on the track, aligned with the track tangent.
  4. Runs a PID controller that uses only the analog line sensor readings
     (2, 5, or 8 TCRT5000) to follow the line.

Default simulator controls:
    Space (Start button) -> start/pause simulation
    Middle mouse button  -> pan | mouse wheel -> zoom
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from hivebr.engine.geometry import clamp

TRACK_PATH = project_root / "config" / "line_track.png"


# ---------------------------------------------------------------------------
# Random Track Generation
# ---------------------------------------------------------------------------
def generate_random_track(
    path: Path,
    width_m: float = 4.0,
    height_m: float = 3.0,
    resolution: float = 0.005,
    line_width_m: float = 0.02,
    seed: int = 7,
):
    """Creates a random closed track and draws it as a black line.

    The curve is a smooth perturbation (Fourier series) of an ellipse, which
    guarantees a closed trajectory with smooth curvature, suitable for a
    line follower. Returns the track centerline points in world coordinates
    (meters).
    """
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


# ---------------------------------------------------------------------------
# PID Line Following Controller
# ---------------------------------------------------------------------------
_CTRL_STATE: dict[int, dict] = {}


def line_pid_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    """PID controller that follows the line using only line sensors.

    The normalized error (``robot.line_error``) is ``-1`` when the line is
    entirely to the right of the robot, ``+1`` when entirely to the left, and
    ``0`` when centered. Since the robot is differential, ``omega`` corrects
    the deviation and ``v`` is reduced in curves.
    """
    line_map = getattr(world, "line_map", None)
    if line_map is None or not hasattr(robot, "read_line_sensors"):
        return {"v": 0.0, "omega": 0.0}

    robot.read_line_sensors(line_map)
    error = robot.line_error

    pid = cfg.get("line_pid", {})
    base_speed = float(pid.get("base_speed", 0.35))
    kp = float(pid.get("kp", 3.0))
    ki = float(pid.get("ki", 0.0))
    kd = float(pid.get("kd", 0.8))
    integral_limit = float(pid.get("integral_limit", 1.0))

    state = _CTRL_STATE.setdefault(id(robot), {"integral": 0.0, "prev": 0.0})

    if robot.line_lost:
        # Line lost: spin slowly in the direction of the last known error.
        state["integral"] = 0.0
        omega = 1.5 * (1.0 if error >= 0.0 else -1.0)
        velocity = base_speed * 0.4
    else:
        state["integral"] = clamp(
            state["integral"] + error * dt, -integral_limit, integral_limit
        )
        derivative = (error - state["prev"]) / dt if dt > 0.0 else 0.0
        omega = kp * error + ki * state["integral"] + kd * derivative
        # Reduce speed on large deviations to allow time to correct.
        velocity = base_speed * max(0.15, 1.0 - 0.6 * abs(error))

    state["prev"] = error

    velocity = clamp(velocity, 0.0, robot.max_speed)
    omega = clamp(omega, -robot.max_omega, robot.max_omega)
    return {"v": velocity, "omega": omega}


# ---------------------------------------------------------------------------
# Initial Pose Setup from Track
# ---------------------------------------------------------------------------
def pose_on_track(points: np.ndarray, index: int = 0, lookahead: int = 12):
    """Returns ``(x, y, theta)`` on the track, aligned with the tangent."""
    n = len(points)
    p0 = points[index % n]
    p1 = points[(index + lookahead) % n]
    theta = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    return float(p0[0]), float(p0[1]), float(theta)


def main():
    parser = argparse.ArgumentParser(description="Line follower with PID (TCRT5000)")
    parser.add_argument("--seed", type=int, default=7, help="track random seed")
    parser.add_argument("--sensors", type=int, default=None, help="number of sensors (2, 5, or 8)")
    parser.add_argument("--regenerate", action="store_true", help="force new track generation")
    args = parser.parse_args()

    config = load_config(project_root / "config" / "line_follower.yaml")

    if args.sensors is not None:
        config["robot"]["num_sensors"] = int(args.sensors)

    if args.regenerate or not TRACK_PATH.exists():
        print(f"Generating random track (seed={args.seed}) -> {TRACK_PATH}")
    points = generate_random_track(TRACK_PATH, seed=args.seed)

    config["world"]["line_map_image"] = str(TRACK_PATH)

    sim = Simulator(config=config, controller=line_pid_controller)

    x0, y0, theta0 = pose_on_track(points)
    sim.robot.set_initial_pose(x0, y0, theta0)
    # Camera is already auto-centered on the track by Simulator.__init__
    # No need to call reset() which would center at origin

    print(
        f"Line follower robot: {sim.robot.num_sensors} sensors | "
        f"initial pose=({x0:.2f}, {y0:.2f}, {math.degrees(theta0):.1f}°) | "
        f"PID kp={config['line_pid']['kp']}, ki={config['line_pid']['ki']}, "
        f"kd={config['line_pid']['kd']}"
    )
    print("Click Start (or press Space) to begin.")

    sim.run()

    stats = sim.robot.lap_statistics()
    if stats["count"]:
        print(
            f"\nLap summary: {stats['count']} lap(s) | "
            f"avg={stats['mean']:.2f}s | best={stats['best']:.2f}s | "
            f"worst={stats['worst']:.2f}s"
        )
        print("Lap times (s):", [f"{t:.2f}" for t in sim.robot.lap_times])
    elif getattr(sim.robot, "finished", False):
        print(f"\nCourse completed in {sim.robot.finish_time:.2f}s.")
    else:
        print("\nSimulation ended without complete laps.")


if __name__ == "__main__":
    main()