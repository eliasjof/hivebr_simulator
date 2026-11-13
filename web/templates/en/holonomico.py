"""Hexagonal holonomic robot: a B-bot that moves in any direction without turning.

The 'hexagonal_holonomic' model has three omnidirectional wheels at 120° and
uses the original simulator kinematics: the {"vx", "vy"} command is converted
into the three wheel speeds through inverse kinematics, respecting the wheel
speed limit.

It can move sideways or backwards without turning first.

Here the controller is a force towards the current waypoint, limited in
speed. The Simulator calls the function at every step with the robot, the goal
and the configuration, and uses the returned dictionary as the command.

How to use: the simulation starts by itself. The robot drives a rectangle around the arena.
"""

import math

from hivebr.engine import Simulator, load_config

# Rectangle driven by the robot: (x, y) points in metres.
ROTA = [(4.0, 3.0), (16.0, 3.0), (16.0, 9.0), (4.0, 9.0)]
GANHO = 1.2               # m/s of speed per metre to the target
VELOCIDADE_MAXIMA = 1.5   # m/s
TOLERANCIA = 0.1          # m; below this the waypoint counts as reached


def controlador_holonomico(robot, world, goal, cfg, dt, lidar_readings=None):
    """Return {"vx", "vy"}: velocity along the world x and y axes."""
    if goal is None:  # route finished
        return {"vx": 0.0, "vy": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    if math.hypot(dx, dy) < TOLERANCIA:
        return {"vx": 0.0, "vy": 0.0}

    vx = GANHO * dx
    vy = GANHO * dy
    # If the total speed exceeds the limit, scale both axes down by the same ratio.
    total = math.hypot(vx, vy)
    if total > VELOCIDADE_MAXIMA:
        vx *= VELOCIDADE_MAXIMA / total
        vy *= VELOCIDADE_MAXIMA / total
    return {"vx": vx, "vy": vy}


if __name__ == "__main__":
    config = load_config("config/default.yaml")
    config["robot"].update({
        "type": "hexagonal_holonomic",   # 3 omnidirectional wheels at 120°
        "initial_pose": [4.0, 3.0, 0.0],
        "radius": 0.3,                   # L: distance from the centre to a wheel
        "wheel_radius": 0.05,            # r: wheel radius
        "max_wheel_speed": 20.0,         # rad/s
    })

    sim = Simulator(config=config, controller=controlador_holonomico)

    # Each waypoint is (x, y, theta). The holonomic robot has no final
    # orientation to reach, so theta is nan (no arrow is drawn).
    sim.set_robot_waypoints(0, [(x, y, math.nan) for x, y in ROTA])

    print("Holonomic robot (hexagonal).")
    sim.run()
    print("Simulation finished.")
