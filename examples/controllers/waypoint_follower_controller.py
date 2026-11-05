from __future__ import annotations

import math
import numpy as np

from hivebr.engine.geometry import wrap_to_pi, clamp


def waypoint_follower_controller(robot,world,goal,cfg,dt,lidar_readings=None):

    if goal is None:
        return {
            "v": 0.0,
            "omega": 0.0
        }

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y

    theta_goal = math.atan2(dy, dx)

    heading_error = wrap_to_pi(
        theta_goal - robot.theta
    )

    k_w = 2.0

    v = robot.max_speed * 0.8

    omega = k_w * heading_error

    omega = clamp(
        omega,
        -robot.max_omega,
        robot.max_omega
    )

    return {
        "v": v,
        "omega": omega
    }

def waypoint_follower_controller_2(robot,world,goal,cfg,dt,lidar_readings=None):
    """
    Controlador simples para seguir waypoints.

    Funciona para:
      - DifferentialRobot
      - BoatRobot

    Retorna:
      {"v": ..., "omega": ...}
    """

    if goal is None:
        return {
            "v": 0.0,
            "omega": 0.0
        }

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y

    distance = math.hypot(dx, dy)

    theta_goal = math.atan2(dy, dx)

    heading_error = wrap_to_pi(
        theta_goal - robot.theta
    )

    # ------------------------
    # Ganhos
    # ------------------------

    k_v = 1.0
    k_w = 2.0

    # ------------------------
    # Velocidade linear
    # ------------------------

    v = k_v * distance

    # reduz velocidade quando está muito desalinhado
    v *= max(0.0, math.cos(heading_error))

    # ------------------------
    # Velocidade angular
    # ------------------------

    omega = k_w * heading_error

    # ------------------------
    # Saturação
    # ------------------------

    v = clamp(
        v,
        0.0,
        robot.max_speed
    )

    omega = clamp(
        omega,
        -robot.max_omega,
        robot.max_omega
    )

    # ------------------------
    # Desaceleração próxima
    # ------------------------

    if distance < 1.0:
        v *= distance

    # ------------------------
    # Parada
    # ------------------------

    goal_tolerance = cfg["waypoints"].get(
        "goal_tolerance",
        0.35
    )

    if distance < goal_tolerance:
        return {
            "v": 0.0,
            "omega": 0.0
        }

    return {
        "v": v,
        "omega": omega
    }