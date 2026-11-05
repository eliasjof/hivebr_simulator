from pathlib import Path
import sys
import math
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from hivebr.engine import Simulator, load_config
from hivebr.engine.geometry import wrap_to_pi, clamp


def my_controller(robot, world, goal, cfg, dt):
    if goal is None:
        return {}
    dx, dy = goal - robot.position
    desired = math.atan2(dy, dx)
    error = wrap_to_pi(desired - robot.theta)
    dist = math.hypot(dx, dy)
    rtype = robot.state()["type"]
    if rtype == "holonomic":
        gain = 1.0
        return {"vx": gain * dx, "vy": gain * dy}
    if rtype == "differential":
        v = robot.max_speed * math.tanh(dist) * max(0.0, math.cos(error))
        omega = clamp(1.5 * error, -robot.max_omega, robot.max_omega)
        return {"v": v, "omega": omega}
    if rtype == "ackermann":
        speed = robot.max_speed * math.tanh(dist) * max(0.15, math.cos(error))
        steer = clamp(1.5 * error, -robot.max_steer, robot.max_steer)
        return {"speed": speed, "steer": steer}
    return {}

if __name__ == "__main__":
    config = load_config(ROOT / "config" / "default.yaml")
    config["robot"]["type"] = "holonomic"
    sim = Simulator(config=config, controller=my_controller)
    sim.run()
