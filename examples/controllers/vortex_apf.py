from __future__ import annotations

import math
import numpy as np

from hivebr.engine.geometry import wrap_to_pi, clamp


# ==========================================================
# UTILITÁRIOS
# ==========================================================

def rotate_90_ccw(v: np.ndarray) -> np.ndarray:
    return np.array([-v[1], v[0]], dtype=float)


def rotate_90_cw(v: np.ndarray) -> np.ndarray:
    return np.array([v[1], -v[0]], dtype=float)


def limit_vector_norm(v: np.ndarray, max_norm: float) -> np.ndarray:
    norm = np.linalg.norm(v)

    if norm < 1e-9:
        return v

    if norm > max_norm:
        return v / norm * max_norm

    return v


def low_pass_filter(name: str, value, alpha: float):
    if not hasattr(vortex_apf_controller, name):
        if isinstance(value, np.ndarray):
            setattr(vortex_apf_controller, name, value.copy())
        else:
            setattr(vortex_apf_controller, name, value)

    previous = getattr(vortex_apf_controller, name)

    filtered = (1.0 - alpha) * previous + alpha * value

    setattr(vortex_apf_controller, name, filtered)

    return filtered


def reset_controller_memory():
    attrs = [
        "filtered_force",
        "last_vx",
        "last_vy",
        "last_v",
        "last_omega",
        "last_speed",
        "last_steer",
    ]

    for attr in attrs:
        if hasattr(vortex_apf_controller, attr):
            delattr(vortex_apf_controller, attr)


# ==========================================================
# CAMPO VORTEX APF USANDO LIDAR_READINGS
# ==========================================================

def vortex_apf_force(
    robot,
    world,
    goal,
    cfg,
    lidar_readings=None
) -> np.ndarray:
    """
    Calcula:

        F = F_att + F_rep_lidar + F_vortex_lidar

    usando as leituras de LiDAR calculadas pelo simulador.

    Cada leitura deve estar no formato:

        (angle, distance, hit_point)
    """

    if goal is None:
        return np.zeros(2)

    if lidar_readings is None:
        lidar_readings = []

    controller_cfg = cfg.get("controller", {})

    k_att = float(
        controller_cfg.get("attractive_gain", 0.8)
    )

    k_rep = float(
        controller_cfg.get("repulsive_gain", 2.5)
    )

    k_vortex = float(
        controller_cfg.get("vortex_gain", 0.8)
    )

    d_s = float(
        controller_cfg.get("repulsive_radius", 5.5)
    )

    max_repulsive_force = float(
        controller_cfg.get("max_repulsive_force", 10.0)
    )

    max_vortex_force = float(
        controller_cfg.get("max_vortex_force", 8.0)
    )

    min_lidar_distance = float(
        controller_cfg.get("min_lidar_distance", 0.08)
    )

    lidar_range = float(
        cfg.get("lidar", {}).get("range", 4.0)
    )

    vortex_direction_mode = controller_cfg.get(
        "vortex_direction",
        "goal"
    ).lower()

    force_filter_alpha = float(
        controller_cfg.get("force_filter_alpha", 0.08)
    )

    q = robot.position
    goal = np.asarray(goal, dtype=float)

    # ======================================================
    # FORÇA ATRATIVA
    # ======================================================

    attractive_force = k_att * (goal - q)

    goal_vec = goal - q
    goal_norm = np.linalg.norm(goal_vec)

    if goal_norm > 1e-9:
        goal_dir = goal_vec / goal_norm
    else:
        goal_dir = np.zeros(2)

    # ======================================================
    # FORÇAS REPULSIVA E VORTEX VIA LIDAR
    # ======================================================

    repulsive_force = np.zeros(2)
    vortex_force = np.zeros(2)

    for angle, distance, hit_point in lidar_readings:

        # Ignora raios sem colisão
        if distance >= lidar_range:
            continue

        d = max(
            float(distance),
            min_lidar_distance
        )

        if d > d_s:
            continue

        hit_point = np.asarray(hit_point, dtype=float)

        away_vec = q - hit_point
        away_norm = np.linalg.norm(away_vec)

        if away_norm < 1e-9:
            away_dir = -np.array(
                [
                    math.cos(angle),
                    math.sin(angle)
                ],
                dtype=float
            )
        else:
            away_dir = away_vec / away_norm

        s = d / d_s
        smooth_weight = (1.0 - s) ** 2

        # ==================================================
        # REPULSÃO RADIAL
        # ==================================================

        rep_i = k_rep * smooth_weight * (
            (1.0 / d) - (1.0 / d_s)
        ) * (
            1.0 / (d ** 2)
        ) * away_dir

        repulsive_force += rep_i

        # ==================================================
        # COMPONENTE VORTEX / TANGENCIAL
        # ==================================================

        tangent_ccw = rotate_90_ccw(away_dir)
        tangent_cw = rotate_90_cw(away_dir)

        if vortex_direction_mode == "ccw":
            tangent = tangent_ccw

        elif vortex_direction_mode == "cw":
            tangent = tangent_cw

        else:
            if np.dot(tangent_ccw, goal_dir) >= np.dot(tangent_cw, goal_dir):
                tangent = tangent_ccw
            else:
                tangent = tangent_cw

        vortex_i = (
            k_vortex
            * smooth_weight
            * np.linalg.norm(rep_i)
            * tangent
        )

        vortex_force += vortex_i

    repulsive_force = limit_vector_norm(
        repulsive_force,
        max_repulsive_force
    )

    vortex_force = limit_vector_norm(
        vortex_force,
        max_vortex_force
    )

    total_force = (
        attractive_force
        + repulsive_force
        + vortex_force
    )

    total_force = low_pass_filter(
        "filtered_force",
        total_force,
        force_filter_alpha
    )

    return total_force


# ==========================================================
# FATOR DE VELOCIDADE VIA LIDAR
# ==========================================================

def lidar_obstacle_speed_factor(
    cfg,
    lidar_readings=None
) -> float:

    if lidar_readings is None:
        lidar_readings = []

    controller_cfg = cfg.get("controller", {})

    lidar_range = float(
        cfg.get("lidar", {}).get("range", 4.0)
    )

    slowdown_distance = float(
        controller_cfg.get("obstacle_slowdown_distance", 4.5)
    )

    min_factor = float(
        controller_cfg.get("min_obstacle_speed_factor", 0.20)
    )

    valid_distances = [
        float(distance)
        for _, distance, _ in lidar_readings
        if distance < lidar_range
    ]

    if not valid_distances:
        return 1.0

    nearest = min(valid_distances)

    if nearest >= slowdown_distance:
        return 1.0

    factor = nearest / slowdown_distance

    return clamp(
        factor,
        min_factor,
        1.0
    )


# ==========================================================
# CONTROLADOR PRINCIPAL
# ==========================================================

def vortex_apf_controller(
    robot,
    world,
    goal,
    cfg,
    dt,
    lidar_readings=None
) -> dict:

    if goal is None:
        return {}

    controller_cfg = cfg.get("controller", {})

    if not bool(controller_cfg.get("enabled", True)):
        return {}

    if lidar_readings is None:
        lidar_readings = []

    force = vortex_apf_force(
        robot,
        world,
        goal,
        cfg,
        lidar_readings
    )

    force_norm = np.linalg.norm(force)

    if force_norm < 1e-8:
        return {}

    robot_type = robot.state().get(
        "type",
        cfg["robot"].get("type", "ackermann")
    ).lower()

    linear_gain = float(
        controller_cfg.get("linear_gain", 0.65)
    )

    angular_gain = float(
        controller_cfg.get("angular_gain", 0.75)
    )

    command_filter_alpha = float(
        controller_cfg.get("command_filter_alpha", 0.10)
    )

    speed_factor = lidar_obstacle_speed_factor(
        cfg,
        lidar_readings
    )

    # ======================================================
    # HOLONÔMICO
    # comando: vx, vy
    # ======================================================

    if robot_type == "holonomic":
        direction = force / force_norm

        speed = robot.max_speed * math.tanh(
            linear_gain * force_norm
        )

        speed *= speed_factor

        vx = speed * direction[0]
        vy = speed * direction[1]

        vx = low_pass_filter(
            "last_vx",
            vx,
            command_filter_alpha
        )

        vy = low_pass_filter(
            "last_vy",
            vy,
            command_filter_alpha
        )

        return {
            "vx": vx,
            "vy": vy
        }

    # ======================================================
    # ROBÔS NÃO HOLONÔMICOS
    # ======================================================

    desired_heading = math.atan2(
        force[1],
        force[0]
    )

    heading_error = wrap_to_pi(
        desired_heading - robot.theta
    )

    # ======================================================
    # DIFERENCIAL
    # comando: v, omega
    # ======================================================

    if robot_type == "differential":
        v = robot.max_speed * math.tanh(
            linear_gain * force_norm
        )

        v *= max(
            0.0,
            math.cos(heading_error)
        )

        v *= speed_factor

        omega = angular_gain * heading_error

        omega = clamp(
            omega,
            -robot.max_omega,
            robot.max_omega
        )

        v = low_pass_filter(
            "last_v",
            v,
            command_filter_alpha
        )

        omega = low_pass_filter(
            "last_omega",
            omega,
            command_filter_alpha
        )

        return {
            "v": v,
            "omega": omega
        }

    # ======================================================
    # ACKERMANN
    # comando: speed, steer
    # ======================================================

    if robot_type == "ackermann":
        distance_to_goal = np.linalg.norm(
            goal - robot.position
        )

        speed = robot.max_speed * math.tanh(
            linear_gain * distance_to_goal
        )

        heading_factor = max(
            0.15,
            math.cos(heading_error)
        )

        speed *= heading_factor

        speed *= speed_factor

        steer = angular_gain * heading_error

        steer = clamp(
            steer,
            -robot.max_steer,
            robot.max_steer
        )

        curvature_speed_gain = float(
            controller_cfg.get("curvature_speed_gain", 2.5)
        )

        curvature_factor = 1.0 / (
            1.0 + curvature_speed_gain * abs(steer)
        )

        speed *= curvature_factor

        max_steer_rate = float(
            controller_cfg.get("max_steer_rate", 0.6)
        )

        if not hasattr(vortex_apf_controller, "last_steer"):
            vortex_apf_controller.last_steer = steer

        delta_steer = steer - vortex_apf_controller.last_steer
        max_delta = max_steer_rate * dt

        delta_steer = clamp(
            delta_steer,
            -max_delta,
            max_delta
        )

        steer = vortex_apf_controller.last_steer + delta_steer

        vortex_apf_controller.last_steer = steer

        speed = low_pass_filter(
            "last_speed",
            speed,
            command_filter_alpha
        )

        return {
            "speed": speed,
            "steer": steer
        }

    return {}