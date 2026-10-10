from __future__ import annotations

import math
import numpy as np
from collections import deque
from enum import Enum, auto

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
        setattr(
            potential_field_controller, name,
            value.copy() if isinstance(value, np.ndarray) else value
        )
    previous = getattr(potential_field_controller, name)
    filtered = (1.0 - alpha) * previous + alpha * value
    setattr(potential_field_controller, name, filtered)
    return filtered


# ==========================================================
# [MOD-6] MÁQUINA DE ESTADOS DE EMERGÊNCIA
# Ref: Behnke (2004) — reactive collision recovery via
#      finite state machine com estados NORMAL, BRAKE e REVERSE.
#      Thrun et al. (2005), "Probabilistic Robotics" —
#      detecção de iminência de colisão por zona crítica de LiDAR.
# ==========================================================

class DriveState(Enum):
    NORMAL  = auto()   # navegação APF padrão
    BRAKE   = auto()   # frenagem de emergência
    REVERSE = auto()   # ré controlada para afastamento


# estado global da máquina
_drive_state: DriveState = DriveState.NORMAL
_reverse_steps_done: int = 0
_reverse_steps_total: int = 0
_reverse_steer: float     = 0.0


def _nearest_front_obstacle(
    lidar_readings: list,
    lidar_range: float,
    front_half_angle_deg: float = 40.0,
) -> float:
    """
    Retorna a menor distância LiDAR dentro do cone frontal
    definido por ±front_half_angle_deg.
    Retorna lidar_range se nenhum ponto no cone.
    """
    half = math.radians(front_half_angle_deg)
    distances = [
        d for angle, d, _ in lidar_readings
        if d < lidar_range and abs(angle) <= half
    ]
    return min(distances) if distances else lidar_range


def _nearest_rear_obstacle(
    lidar_readings: list,
    lidar_range: float,
    rear_half_angle_deg: float = 40.0,
) -> float:
    """
    Retorna a menor distância LiDAR dentro do cone traseiro
    definido por |angle| > π - rear_half_angle_deg.
    Retorna lidar_range se nenhum ponto no cone.
    """
    half = math.radians(rear_half_angle_deg)
    distances = [
        d for angle, d, _ in lidar_readings
        if d < lidar_range and abs(angle) > (math.pi - half)
    ]
    return min(distances) if distances else lidar_range


def collision_recovery_fsm(
    robot,
    lidar_readings: list,
    cfg: dict,
    dt: float,
    current_steer: float,
) -> dict | None:
    """
    Máquina de estados finita (FSM) de recuperação de colisão.

    Estados e transições
    ────────────────────
    NORMAL ──[d_front < d_brake]──► BRAKE
    BRAKE  ──[speed ≈ 0]──────────► REVERSE   (inicia contagem de passos)
    REVERSE──[passos esgotados]────► NORMAL
    REVERSE──[d_rear < d_safe]─────► NORMAL    (obstáculo atrás: para ré)

    Fundamento teórico (Behnke, 2004):
        A separação em três fases — detecção → parada brusca →
        recuo controlado — evita a situação em que o APF tenta
        redirecionar o veículo enquanto ele já está a poucos
        centímetros do obstáculo, o que resultaria em colisão
        antes de qualquer manobra ser concluída.

        A ré é executada com o esterçamento oposto ao da
        última curva (steer_reverse = -steer_anterior), pois
        ao dar ré com o volante à direita um veículo Ackermann
        descreve um arco que afasta sua frente do obstáculo —
        comportamento idêntico ao de um motorista humano
        recuando após uma frenagem de emergência.

    Retorna:
        dict {"speed": v, "steer": δ}  durante BRAKE/REVERSE
        None                            durante NORMAL (FSM inativa)
    """
    global _drive_state, _reverse_steps_done
    global _reverse_steps_total, _reverse_steer

    controller_cfg = cfg.get("controller", {})
    lidar_range = cfg.get("lidar", {}).get("range", 4.0)

    # limites configuráveis
    d_brake   = float(controller_cfg.get("emergency_brake_distance",  0.35))
    d_safe    = float(controller_cfg.get("emergency_safe_distance",   0.55))
    d_rear    = float(controller_cfg.get("emergency_rear_clearance",  0.40))
    rev_speed = float(controller_cfg.get("reverse_speed",            -0.25))
    rev_time  = float(controller_cfg.get("reverse_duration_s",        1.2))

    d_front = _nearest_front_obstacle(lidar_readings, lidar_range)
    d_back  = _nearest_rear_obstacle(lidar_readings,  lidar_range)

    # ----------------------------------------------------------
    # TRANSIÇÕES
    # ----------------------------------------------------------
    if _drive_state == DriveState.NORMAL:
        if d_front - robot.radius < d_brake:
            _drive_state = DriveState.BRAKE

    elif _drive_state == DriveState.BRAKE:
        # permanece freando até o robô parar (velocidade ~0)
        # ou a distância frontal voltar a ser segura
        robot_speed = getattr(robot, "speed", None)
        speed_ok = (robot_speed is None) or (abs(robot_speed) < 0.05)

        if d_front - robot.radius >= d_safe:
            # obstáculo se afastou (e.g., obstáculo dinâmico)
            _drive_state = DriveState.NORMAL
        elif speed_ok:
            # passou pela frenagem — inicia ré
            _drive_state = DriveState.REVERSE
            _reverse_steps_total = max(1, int(round(rev_time / dt)))
            _reverse_steps_done  = 0
            # esterçamento de ré = oposto ao anterior
            # (geometria Ackermann: ré com volante à direita
            #  abre a frente para a esquerda)
            _reverse_steer = clamp(
                -current_steer,
                -robot.max_steer,
                robot.max_steer
            )

    elif _drive_state == DriveState.REVERSE:
        _reverse_steps_done += 1

        # sai da ré se: tempo esgotado OU obstáculo atrás muito perto
        if _reverse_steps_done >= _reverse_steps_total:
            _drive_state = DriveState.NORMAL
        elif d_back < d_rear:
            # obstáculo detectado atrás — para a ré imediatamente
            _drive_state = DriveState.NORMAL

    # ----------------------------------------------------------
    # SAÍDAS POR ESTADO
    # ----------------------------------------------------------
    if _drive_state == DriveState.NORMAL:
        return None  # deixa APF assumir normalmente

    if _drive_state == DriveState.BRAKE:
        return {"speed": 0.0, "steer": 0.0}

    if _drive_state == DriveState.REVERSE:
        return {"speed": rev_speed, "steer": _reverse_steer}

    return None  # fallback


# ==========================================================
# [MOD-1] DETECÇÃO DE MÍNIMO LOCAL
# ==========================================================

_position_history: deque = deque(maxlen=30)

def detect_local_minima(
    robot_position: np.ndarray,
    F_total: np.ndarray,
    goal: np.ndarray,
    stagnation_radius: float = 0.15,
    angle_threshold_deg: float = 90.0,
) -> bool:
    global _position_history
    _position_history.append(robot_position.copy())

    if len(_position_history) < _position_history.maxlen:
        return False

    positions = np.array(_position_history)
    spread = np.max(np.linalg.norm(positions - positions[0], axis=1))
    stagnated = spread < stagnation_radius

    goal_vec = goal - robot_position
    norm_F = np.linalg.norm(F_total)
    norm_g = np.linalg.norm(goal_vec)
    diverged = False
    if norm_F > 1e-6 and norm_g > 1e-6:
        cos_angle = np.dot(F_total, goal_vec) / (norm_F * norm_g)
        cos_angle = clamp(cos_angle, -1.0, 1.0)
        angle_deg = math.degrees(math.acos(cos_angle))
        diverged = angle_deg > angle_threshold_deg

    return stagnated and diverged


# ==========================================================
# [MOD-2] SUBOBJETIVO VIRTUAL
# ==========================================================

def compute_virtual_subgoal(
    robot_position: np.ndarray,
    goal: np.ndarray,
    F_rep: np.ndarray,
    virtual_offset: float = 2.0,
) -> np.ndarray:
    rep_norm = np.linalg.norm(F_rep)
    if rep_norm < 1e-6:
        return goal

    rep_dir = F_rep / rep_norm
    perp_cw  = np.array([ rep_dir[1], -rep_dir[0]])
    perp_ccw = np.array([-rep_dir[1],  rep_dir[0]])

    goal_dir = goal - robot_position
    goal_dir_norm = np.linalg.norm(goal_dir)
    if goal_dir_norm < 1e-6:
        return goal
    goal_dir = goal_dir / goal_dir_norm

    escape_dir = perp_cw if np.dot(perp_cw, goal_dir) >= np.dot(perp_ccw, goal_dir) else perp_ccw
    return robot_position + escape_dir * virtual_offset


# ==========================================================
# [MOD-3] FORÇA TANGENCIAL
# ==========================================================

def tangential_repulsive_force(
    robot_position: np.ndarray,
    robot_theta: float,
    lidar_readings: list,
    lidar_range: float,
    d_s: float,
    k_tang: float,
    min_distance: float,
) -> np.ndarray:
    F_tang = np.zeros(2)

    for angle, distance, hit_point in lidar_readings:
        if distance >= lidar_range:
            continue
        d = max(distance, min_distance)
        if d > d_s:
            continue

        hit_point = np.asarray(hit_point, dtype=float)
        r = robot_position - hit_point
        r_norm = np.linalg.norm(r)
        if r_norm < 1e-9:
            continue

        r_hat    = r / r_norm
        tang_cw  = np.array([ r_hat[1], -r_hat[0]])
        tang_ccw = np.array([-r_hat[1],  r_hat[0]])
        heading  = np.array([math.cos(robot_theta), math.sin(robot_theta)])
        tang     = tang_cw if np.dot(tang_cw, heading) >= np.dot(tang_ccw, heading) else tang_ccw

        magnitude = k_tang * ((1.0 / d) - (1.0 / d_s)) * (1.0 / d ** 2)
        weight    = max(math.cos(angle), 0.0)
        F_tang   += weight * magnitude * tang

    return F_tang


# ==========================================================
# CAMPO POTENCIAL
# ==========================================================

def potential_field_force(robot, goal, cfg, lidar_readings=None):
    if goal is None:
        return {
            "attractive": np.zeros(2), "repulsive": np.zeros(2),
            "tangential": np.zeros(2), "total":     np.zeros(2),
            "in_local_minima": False,  "virtual_goal": None,
        }

    if lidar_readings is None:
        lidar_readings = []

    controller_cfg = cfg.get("controller", {})
    k_att   = float(controller_cfg.get("attractive_gain",     1.0))
    k_rep   = float(controller_cfg.get("repulsive_gain",      4.0))
    k_tang  = float(controller_cfg.get("tangential_gain",     1.5))
    d_s     = float(controller_cfg.get("repulsive_radius",    5.0))
    max_rep = float(controller_cfg.get("max_repulsive_force", 15.0))
    min_d   = float(controller_cfg.get("min_lidar_distance",  0.08))
    alpha   = float(controller_cfg.get("force_filter_alpha",  0.1))
    lidar_range          = float(cfg.get("lidar", {}).get("range", 4.0))
    goal_repulsive_decay = float(controller_cfg.get("goal_repulsive_decay", 2.0))
    stagnation_radius    = float(controller_cfg.get("stagnation_radius",     0.15))
    angle_threshold_deg  = float(controller_cfg.get("local_minima_angle_deg",90.0))
    virtual_offset       = float(controller_cfg.get("virtual_subgoal_offset", 2.0))

    q    = robot.position
    goal = np.asarray(goal, dtype=float)[:2]
    goal_distance = np.linalg.norm(goal - q)

    # força atrativa saturada
    goal_vector = goal - q
    goal_dist   = np.linalg.norm(goal_vector)
    if goal_dist > 1e-6:
        F_att = k_att * (goal_vector / goal_dist) * min(goal_dist, 1.5)
    else:
        F_att = np.zeros(2)

    # força repulsiva (Khatib 1986)
    F_rep = np.zeros(2)
    for angle, distance, hit_point in lidar_readings:
        if distance >= lidar_range:
            continue
        d = max(distance - robot.radius, min_d)
        if d > d_s:
            continue
        hit_point = np.asarray(hit_point, dtype=float)
        r = q - hit_point
        r_norm = np.linalg.norm(r)
        r_hat = (r / r_norm if r_norm >= 1e-9
                 else -np.array([math.cos(angle), math.sin(angle)]))
        F_rep_i     = k_rep * ((1.0 / d) - (1.0 / d_s)) * (1.0 / d ** 2) * r_hat
        weight      = max(math.cos(angle), 0.0)
        goal_weight = 1.0 - math.exp(-goal_distance / goal_repulsive_decay)
        F_rep      += goal_weight * weight * F_rep_i
    F_rep = limit_vector_norm(F_rep, max_rep)

    # força tangencial
    F_tang = tangential_repulsive_force(
        q, robot.theta, lidar_readings, lidar_range, d_s, k_tang, min_d
    )
    F_tang = limit_vector_norm(F_tang, max_rep * 0.5)

    F_total = F_att + F_rep + F_tang

    # detecção de mínimo local
    in_local_minima = detect_local_minima(
        q, F_total, goal, stagnation_radius, angle_threshold_deg
    )

    # subobjetivo virtual
    virtual_goal = None
    if in_local_minima:
        virtual_goal = compute_virtual_subgoal(q, goal, F_rep, virtual_offset)
        vg_vec  = virtual_goal - q
        vg_dist = np.linalg.norm(vg_vec)
        if vg_dist > 1e-6:
            F_att_escape = k_att * (vg_vec / vg_dist) * min(vg_dist, 1.5)
            F_total = F_att_escape + F_rep + F_tang

    F_total = low_pass_filter("filtered_force", F_total, alpha)

    return {
        "attractive": F_att, "repulsive": F_rep,
        "tangential": F_tang, "total":    F_total,
        "in_local_minima": in_local_minima, "virtual_goal": virtual_goal,
    }


# ==========================================================
# FATOR DE VELOCIDADE
# ==========================================================

def lidar_obstacle_speed_factor(cfg, lidar_readings=None):
    if lidar_readings is None:
        lidar_readings = []
    controller_cfg    = cfg.get("controller", {})
    lidar_range       = cfg.get("lidar", {}).get("range", 4.0)
    slowdown_distance = controller_cfg.get("obstacle_slowdown_distance", 4.0)
    min_factor        = controller_cfg.get("min_obstacle_speed_factor",  0.2)
    valid = [d for _, d, _ in lidar_readings if d < lidar_range]
    if not valid:
        return 1.0
    nearest = min(valid)
    if nearest >= slowdown_distance:
        return 1.0
    return clamp(nearest / slowdown_distance, min_factor, 1.0)


# ==========================================================
# CONTROLADOR PRINCIPAL
# ==========================================================

def potential_field_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {}

    controller_cfg = cfg.get("controller", {})
    if not controller_cfg.get("enabled", True):
        return {}

    if lidar_readings is None:
        lidar_readings = []

    # ----------------------------------------------------------
    # [MOD-6] FSM DE EMERGÊNCIA — tem prioridade sobre o APF
    # Passa o último steer filtrado para o cálculo da ré
    # ----------------------------------------------------------
    last_steer = getattr(potential_field_controller, "steer", 0.0)
    fsm_cmd = collision_recovery_fsm(robot, lidar_readings, cfg, dt, last_steer)
    if fsm_cmd is not None:
        # aplica filtro suave mesmo nos comandos de emergência
        alpha = controller_cfg.get("command_filter_alpha", 0.1)
        fsm_cmd["speed"] = low_pass_filter("speed", fsm_cmd["speed"], alpha)
        fsm_cmd["steer"] = low_pass_filter("steer", fsm_cmd["steer"], alpha)
        return fsm_cmd

    # ----------------------------------------------------------
    # APF normal
    # ----------------------------------------------------------
    forces = potential_field_force(robot, goal, cfg, lidar_readings)
    F      = forces["total"]
    norm   = np.linalg.norm(F)
    if norm < 1e-8:
        return {}

    robot_type = robot.state().get(
        "type", cfg["robot"].get("type", "ackermann")
    ).lower()

    k_lin        = controller_cfg.get("linear_gain",         0.8)
    alpha        = controller_cfg.get("command_filter_alpha", 0.1)
    speed_factor = lidar_obstacle_speed_factor(cfg, lidar_readings)


    if robot_type == "holonomic":
        F_dir = F / norm
        vx = robot.max_speed * F_dir[0]
        vy = robot.max_speed * F_dir[1]

        vx = low_pass_filter("vx", vx, alpha)
        vy = low_pass_filter("vy", vy, alpha)

        return {
            "vx": vx,
            "vy": vy
        }

    elif robot_type == "differential" or robot_type == "boat":
        theta_des = math.atan2(F[1], F[0])
        heading_error = wrap_to_pi(
            theta_des - robot.theta
        )

        v = robot.max_speed * math.tanh(norm)

        v *= max(
            0.0,
            math.cos(heading_error)
        )

        omega = (
            2.0 * heading_error
        )

        omega = clamp(
            omega,
            -robot.max_omega,
            robot.max_omega
        )

        v *= speed_factor

        v = low_pass_filter("v", v, alpha)
        omega = low_pass_filter("omega", omega, alpha)

        return {
            "v": v,
            "omega": omega
        }
    if robot_type == "ackermann":
        wheelbase          = float(controller_cfg.get("wheelbase", getattr(robot, "wheelbase", 0.33)))
        lateral_gain       = float(controller_cfg.get("lateral_field_gain",   0.35))
        goal_capture_radius= float(controller_cfg.get("goal_capture_radius",  1.0))
        goal_stop_radius   = float(cfg["waypoints"].get("goal_tolerance", 0.35)) 

        goal_arr      = np.asarray(goal, dtype=float)[:2]
        goal_vector   = goal_arr - robot.position
        goal_distance = np.linalg.norm(goal_vector)
        lookahead     = clamp(0.5 + 0.3 * goal_distance, 0.6, 1.5)

        if goal_distance < goal_stop_radius:
            print("Goal reached! Stopping.")
            return {"speed": 0.0, "steer": 0.0}

        R_wr = np.array([
            [ math.cos(robot.theta), math.sin(robot.theta)],
            [-math.sin(robot.theta), math.cos(robot.theta)],
        ])
        F_body    = R_wr @ F
        F_body[1] *= lateral_gain
        F_body[0]  = max(F_body[0], 0.2)

        if goal_distance < goal_capture_radius:
            theta_goal    = math.atan2(goal_vector[1], goal_vector[0])
            heading_error = wrap_to_pi(theta_goal - robot.theta)
            steer = clamp(1.5 * heading_error, -robot.max_steer, robot.max_steer)
            speed = max(robot.max_speed * 0.35 * math.exp(-2.0 * abs(heading_error)), 0.15)
            speed = low_pass_filter("speed", speed, alpha)
            steer = low_pass_filter("steer", steer, alpha)
            return {"speed": speed, "steer": steer}

        F_norm = np.linalg.norm(F_body)
        if F_norm < 1e-6:
            return {}

        direction    = F_body / F_norm
        target_local = direction * lookahead
        x_t, y_t    = target_local

        curvature = (2.0 * y_t) / (lookahead ** 2)
        steer     = math.atan(wheelbase * curvature)
        steer     = clamp(steer, -robot.max_steer, robot.max_steer)

        # [MOD-4] lei velocidade-curvatura (Lefévre 2014)
        speed            = robot.max_speed * math.tanh(k_lin * norm)
        kappa_normalized = abs(steer) / robot.max_steer
        speed           *= (1.0 - 0.7 * kappa_normalized ** 0.5)

        # [MOD-5] redução em mínimo local
        if forces.get("in_local_minima", False):
            speed *= 0.5

        speed *= speed_factor
        speed  = max(0.4, speed)

        speed = low_pass_filter("speed", speed, alpha)
        steer = low_pass_filter("steer", steer, alpha)

        return {"speed": speed, "steer": steer}

    return {}
