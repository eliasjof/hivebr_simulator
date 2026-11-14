"""Activity: kinematics of a holonomic robot (vx and vy).

The hexagonal robot accepts the command {"vx", "vy"}: it moves in any direction
without turning first. Complete the controller to drive the robot to (12, 8).

Hint: vx and vy should be proportional to dx and dy; clamp the vector norm.
"""

import math

from hivebr.engine import Simulator, load_config

ALVO = (12.0, 8.0)
GANHO = 1.2               # m/s per meter of distance
VELOCIDADE_MAXIMA = 1.5   # m/s
TOLERANCIA = 0.10         # m


def controlador_holonomico(robot, world, goal, cfg, dt, lidar_readings=None):
    """Return {"vx", "vy"} for the holonomic robot."""
    if goal is None:
        return {"vx": 0.0, "vy": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    if math.hypot(dx, dy) < TOLERANCIA:
        return {"vx": 0.0, "vy": 0.0}

    # TODO: compute vx = GANHO * dx and vy = GANHO * dy.
    vx = 0.0
    vy = 0.0

    total = math.hypot(vx, vy)
    if total > VELOCIDADE_MAXIMA:
        vx *= VELOCIDADE_MAXIMA / total
        vy *= VELOCIDADE_MAXIMA / total
    return {"vx": vx, "vy": vy}


def rodar(sim, limite=60.0):
    """Run the simulation until the last waypoint or the time limit."""
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["robot"].update({
        "type": "hexagonal_holonomic",
        "initial_pose": [2.0, 2.0, 0.0],
        "radius": 0.3,
        "wheel_radius": 0.05,
        "max_wheel_speed": 20.0,
    })
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador_holonomico)
    sim.set_robot_waypoints(0, [(ALVO[0], ALVO[1], math.nan)])

    print(f"Goal: {ALVO}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    print("Simulation finished.")
