from copy import deepcopy

from .holonomic import HolonomicRobot
from .differential import DifferentialRobot
from .ackermann import AckermannRobot
from .boat import BoatRobot
from .differential_firstorder import DifferentialRobotFirstOrder
from .line_follower import LineFollowerRobot
from .hexagonal_holonomic import HexagonalHolonomicRobot


def create_robot(config: dict):
    robot_type = config["robot"].get("type", "ackermann").lower()
    if robot_type in ["holonomic", "omni", "omnidirectional"]:
        return HolonomicRobot(config)    
    elif robot_type in ["hexagonal_holonomic", "hexagonal", "hex_holonomic", "3wheel_holonomic"]:
        return HexagonalHolonomicRobot(config)
    elif robot_type in ["ackermann", "car", "racecar"]:
        return AckermannRobot(config)
    elif robot_type == "boat":
        return BoatRobot(config)
    elif robot_type in ["line_follower", "linefollower", "line", "line_tracker", "tcrt5000",
                        "differential_line_follower"]:
        return LineFollowerRobot(config)
    elif robot_type in ["differential_firstorder", "firstorder", "diff_tau"]:            
        return DifferentialRobotFirstOrder(config)
    elif robot_type in ["differential", "diff", "unicycle", "nonholonomic"]:
        return DifferentialRobot(config)
    else:
        print(f"Tipo de robô desconhecido: {robot_type}, using differential as default.")
        return DifferentialRobot(config)


    raise ValueError(f"Tipo de robô desconhecido: {robot_type}")


def create_fleet(config: dict) -> list:
    """Build the list of B-bots from ``config['robots']``.

    Falls back to a single robot built from ``config['robot']`` when no fleet
    is declared, so mono-robot scenarios are just N=1. Each entry may override
    any field of ``config['robot']`` (type, initial_pose, radius, ...) and may
    carry an optional ``color`` used for rendering and path tracing.
    """
    specs = config.get("robots")
    if not specs:
        return [create_robot(config)]

    palette = list(config.get("colors", {}).get("fleet", []))
    robots = []
    for index, spec in enumerate(specs):
        merged = deepcopy(config)
        robot_cfg = dict(config.get("robot", {}))
        robot_cfg.update({k: v for k, v in spec.items() if k != "id" and k != "color"})
        merged["robot"] = robot_cfg

        color = spec.get("color")
        if color is None and palette:
            color = palette[index % len(palette)]
        if color is not None:
            merged["colors"] = dict(config.get("colors", {}))
            merged["colors"]["robot"] = list(color)
            merged["colors"]["path"] = list(color)

        robots.append(create_robot(merged))
    return robots

__all__ = ["create_robot", "create_fleet", "HolonomicRobot", "DifferentialRobot", "DifferentialRobotFirstOrder", "AckermannRobot", "BoatRobot", "LineFollowerRobot", "HexagonalHolonomicRobot"]
