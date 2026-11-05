from __future__ import annotations

import math
import numpy as np

from hivebr.engine.geometry import wrap_to_pi, clamp


def simple_ackermann_controller(
    robot,
    world,
    goal,
    cfg,
    dt,
    lidar_readings=None
):
    """
    Controlador simples Ackermann:
    - vai direto ao waypoint
    - ignora obstáculos
    - steering proporcional
    - velocidade reduz em curvas
    """

    if goal is None:
        return {
            "speed": 0.0,
            "steer": 0.0
        }

    # ==========================================================
    # CONFIG
    # ==========================================================

    controller_cfg = cfg.get("controller", {})

    k_steer = float(
        controller_cfg.get("heading_gain", 2.0)
    )

    goal_tolerance = float(
        cfg.get("waypoints", {}).get(
            "goal_tolerance",
            0.4
        )
    )

    # ==========================================================
    # POSIÇÃO
    # ==========================================================

    q = robot.position

    gx, gy = goal

    dx = gx - q[0]
    dy = gy - q[1]

    dist = math.hypot(dx, dy)

    # ==========================================================
    # ÂNGULO PARA META
    # ==========================================================

    theta_goal = math.atan2(dy, dx)

    heading_error = wrap_to_pi(
        theta_goal - robot.theta
    )

    # ==========================================================
    # STEERING
    # ==========================================================

    steer = k_steer * heading_error

    steer = clamp(
        steer,
        -robot.max_steer,
        robot.max_steer
    )

    # ==========================================================
    # VELOCIDADE
    # ==========================================================

    speed = robot.max_speed

    # reduz velocidade em curvas fortes
    curvature_factor = (
        abs(steer) / robot.max_steer
    )

    speed *= (
        1.0 - 0.7 * curvature_factor
    )

    # velocidade mínima
    speed = max(speed, 0.3)

    # reduz ao aproximar do alvo
    if dist < 2.0:

        speed *= dist / 2.0

        speed = max(speed, 0.2)

    # ==========================================================
    # CHEGOU
    # ==========================================================

    if dist < goal_tolerance:

        return {
            "speed": 0.0,
            "steer": 0.0,
            "goal_reached": True
        }

    # ==========================================================
    # RETORNO
    # ==========================================================

    return {
        "speed": speed,
        "steer": steer
    }