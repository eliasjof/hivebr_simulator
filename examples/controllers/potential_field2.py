from __future__ import annotations

import math
import numpy as np

from hivebr.engine.geometry import wrap_to_pi, clamp


# ==========================================================
# UTILITÁRIOS
# ==========================================================

def limit_vector_norm(v: np.ndarray, max_norm: float) -> np.ndarray:

    norm = np.linalg.norm(v)

    if norm < 1e-9:
        return v

    if norm > max_norm:
        return v / norm * max_norm

    return v


def low_pass_filter(name: str, value, alpha: float):

    if not hasattr(potential_field_controller, name):

        if isinstance(value, np.ndarray):
            setattr(
                potential_field_controller,
                name,
                value.copy()
            )

        else:
            setattr(
                potential_field_controller,
                name,
                value
            )

    previous = getattr(
        potential_field_controller,
        name
    )

    filtered = (
        (1.0 - alpha) * previous
        + alpha * value
    )

    setattr(
        potential_field_controller,
        name,
        filtered
    )

    return filtered


# ==========================================================
# CAMPO POTENCIAL
# ==========================================================

def potential_field_force(
    robot,
    goal,
    cfg,
    lidar_readings=None
):

    if goal is None:

        return {
            "attractive": np.zeros(2),
            "repulsive": np.zeros(2),
            "total": np.zeros(2)
        }

    if lidar_readings is None:
        lidar_readings = []

    controller_cfg = cfg.get("controller", {})

    k_att = float(
        controller_cfg.get(
            "attractive_gain",
            1.0
        )
    )

    k_rep = float(
        controller_cfg.get(
            "repulsive_gain",
            4.0
        )
    )

    d_s = float(
        controller_cfg.get(
            "repulsive_radius",
            5.0
        )
    )

    max_repulsive = float(
        controller_cfg.get(
            "max_repulsive_force",
            15.0
        )
    )

    min_distance = float(
        controller_cfg.get(
            "min_lidar_distance",
            0.08
        )
    )

    lidar_range = float(
        cfg.get(
            "lidar",
            {}
        ).get(
            "range",
            4.0
        )
    )

    alpha = float(
        controller_cfg.get(
            "force_filter_alpha",
            0.1
        )
    )
    

    q = robot.position
    goal = np.asarray(goal, dtype=float)

    goal_distance = np.linalg.norm(goal - q)

    goal_repulsive_decay = float(
        controller_cfg.get(
            "goal_repulsive_decay",
            2.0
        )
    )

    # ======================================================
    # FORÇA ATRATIVA SATURADA
    # ======================================================

    goal_vector = goal - q
    goal_dist = np.linalg.norm(goal_vector)

    if goal_dist > 1e-6:

        direction = goal_vector / goal_dist

        F_att = (
            k_att
            * direction
            * min(goal_dist, 1.5)
        )

    else:

        F_att = np.zeros(2)

    # ======================================================
    # FORÇA REPULSIVA
    # ======================================================

    F_rep = np.zeros(2)

    for angle, distance, hit_point in lidar_readings:

        if distance >= lidar_range:
            continue

        r_robot = robot.radius

        d = max(
            distance - r_robot,
            min_distance
        )

        if d > d_s:
            continue

        hit_point = np.asarray(
            hit_point,
            dtype=float
        )

        r = q - hit_point

        r_norm = np.linalg.norm(r)

        if r_norm < 1e-9:

            r_hat = -np.array([
                math.cos(angle),
                math.sin(angle)
            ])

        else:

            r_hat = r / r_norm

        F_rep_i = (
            k_rep
            * ((1.0 / d) - (1.0 / d_s))
            * (1.0 / (d ** 2))
            * r_hat
        )

        # peso frontal
        weight = math.cos(angle)
        weight = max(weight, 0.0)

        # F_rep += weight * F_rep_i
        # reduz repulsão perto do alvo
        goal_weight = 1.0 - math.exp(
            -goal_distance / goal_repulsive_decay
        )

        F_rep += (
            goal_weight
            * weight
            * F_rep_i
        )

    F_rep = limit_vector_norm(
        F_rep,
        max_repulsive
    )

    # ======================================================
    # RESULTANTE
    # ======================================================

    F_total = F_att + F_rep

    # filtro temporal
    F_total = low_pass_filter(
        "filtered_force",
        F_total,
        alpha
    )

    return {
        "attractive": F_att,
        "repulsive": F_rep,
        "total": F_total
    }


# ==========================================================
# FATOR DE VELOCIDADE
# ==========================================================

def lidar_obstacle_speed_factor(
    cfg,
    lidar_readings=None
):

    if lidar_readings is None:
        lidar_readings = []

    controller_cfg = cfg.get(
        "controller",
        {}
    )

    lidar_range = cfg.get(
        "lidar",
        {}
    ).get(
        "range",
        4.0
    )

    slowdown_distance = controller_cfg.get(
        "obstacle_slowdown_distance",
        4.0
    )

    min_factor = controller_cfg.get(
        "min_obstacle_speed_factor",
        0.2
    )

    valid = [
        d for _, d, _ in lidar_readings
        if d < lidar_range
    ]

    if not valid:
        return 1.0

    nearest = min(valid)

    if nearest >= slowdown_distance:
        return 1.0

    factor = nearest / slowdown_distance

    return clamp(
        factor,
        min_factor,
        1.0
    )


# ==========================================================
# CONTROLADOR
# ==========================================================

def potential_field_controller(
    robot,
    world,
    goal,
    cfg,
    dt,
    lidar_readings=None
):

    if goal is None:
        return {}

    controller_cfg = cfg.get(
        "controller",
        {}
    )

    if not controller_cfg.get(
        "enabled",
        True
    ):
        return {}

    forces = potential_field_force(
        robot,
        goal,
        cfg,
        lidar_readings
    )

    F = forces["total"]

    norm = np.linalg.norm(F)

    if norm < 1e-8:
        return {}

    robot_type = robot.state().get(
        "type",
        cfg["robot"].get(
            "type",
            "ackermann"
        )
    ).lower()

    k_lin = controller_cfg.get(
        "linear_gain",
        0.8
    )

    alpha = controller_cfg.get(
        "command_filter_alpha",
        0.1
    )

    speed_factor = lidar_obstacle_speed_factor(
        cfg,
        lidar_readings
    )

    # ======================================================
    # ACKERMANN
    # ======================================================

    if robot_type == "ackermann":

        wheelbase = float(
            controller_cfg.get(
                "wheelbase",
                getattr(robot, "wheelbase", 0.33)
            )
        )

        lookahead = float(
            controller_cfg.get(
                "lookahead_distance",
                1.5
            )
        )

        

        lateral_gain = float(
            controller_cfg.get(
                "lateral_field_gain",
                0.35
            )
        )

        goal_capture_radius = float(
            controller_cfg.get(
                "goal_capture_radius",
                1.0
            )
        )

        goal_stop_radius = float(
            controller_cfg.get(
                "goal_stop_radius",
                0.25
            )
        )

        # ==================================================
        # DISTÂNCIA AO OBJETIVO
        # ==================================================

        goal_vector = goal - robot.position

        goal_distance = np.linalg.norm(
            goal_vector
        )
        lookahead = clamp(0.5 + 0.3 * goal_distance, 0.6, 1.5)

        # ==================================================
        # PAROU NO OBJETIVO
        # ==================================================

        if goal_distance < goal_stop_radius:

            return {
                "speed": 0.0,
                "steer": 0.0
            }

        # ==================================================
        # REFERENCIAL DO ROBÔ
        # ==================================================

        R_wr = np.array([
            [
                math.cos(robot.theta),
                math.sin(robot.theta)
            ],
            [
                -math.sin(robot.theta),
                math.cos(robot.theta)
            ]
        ])

        F_body = R_wr @ F

        # reduz componente lateral
        F_body[1] *= lateral_gain

        # evita campo para trás
        F_body[0] = max(
            F_body[0],
            0.2
        )

        # ==================================================
        # CAPTURA FINAL
        # ==================================================

        if goal_distance < goal_capture_radius:

            theta_goal = math.atan2(
                goal_vector[1],
                goal_vector[0]
            )

            heading_error = wrap_to_pi(
                theta_goal - robot.theta
            )

            steer = clamp(
                1.5 * heading_error,
                -robot.max_steer,
                robot.max_steer
            )

            speed = (
                robot.max_speed
                * 0.35
                * math.exp(
                    -2.0 * abs(heading_error)
                )
            )

            speed = max(speed, 0.15)

            speed = low_pass_filter(
                "speed",
                speed,
                alpha
            )

            steer = low_pass_filter(
                "steer",
                steer,
                alpha
            )

            return {
                "speed": speed,
                "steer": steer
            }

        # ==================================================
        # PURE PURSUIT SOBRE O CAMPO
        # ==================================================

        F_norm = np.linalg.norm(F_body)

        if F_norm < 1e-6:
            return {}

        direction = F_body / F_norm

        target_local = direction * lookahead

        x_t = target_local[0]
        y_t = target_local[1]

        curvature = (
            2.0 * y_t
        ) / (
            lookahead ** 2
        )

        steer = math.atan(
            wheelbase * curvature
        )

        steer = clamp(
            steer,
            -robot.max_steer,
            robot.max_steer
        )

        # ==================================================
        # VELOCIDADE
        # ==================================================

        speed = (
            robot.max_speed
            * math.tanh(k_lin * norm)
        )

        steer_ratio = (
            abs(steer)
            / robot.max_steer
        )

        speed *= (
            1.0 - 0.7 * steer_ratio
        )

        speed *= speed_factor

        speed = max(0.4, speed)

        # ==================================================
        # FILTROS
        # ==================================================

        speed = low_pass_filter(
            "speed",
            speed,
            alpha
        )

        steer = low_pass_filter(
            "steer",
            steer,
            alpha
        )

        return {
            "speed": speed,
            "steer": steer
        }

    return {}