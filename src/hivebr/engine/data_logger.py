"""
data_logger.py
--------------
DataLogger genérico para hivebr.engine.

Salva em pickle: suporta goal=None, waypoints mistos, qualquer tipo de robô.

Comportamento de gravação
-------------------------
- Inicia gravação quando há waypoints ativos no WaypointManager.
- Pausa gravação quando não há mais waypoints a seguir.
- Reinicia um novo segmento quando novos waypoints são adicionados.
- Cada segmento é identificado pelo campo `segment` nos frames.

Uso
---
    from hivebr.engine.data_logger import DataLogger

    logger = DataLogger()
    sim    = Simulator(controller=ctrl, draw_callback=logger.draw_callback)
    sim.run()

    logger.save("run_01.pkl")
    logger.plot()

    # Carregar e plotar depois
    log = DataLogger.load("run_01.pkl")
    log.plot_log()
"""

from __future__ import annotations

import pickle
import numpy as np
from dataclasses import dataclass, field


# ──────────────────────────────────────────────────────────────
# Campos por tipo de robô
# ──────────────────────────────────────────────────────────────

# Ação de controle (saída do controller, antes do step)
_ROBOT_CMD_FIELDS = {
    "holonomic":    ["vx", "vy"],
    "differential": ["v", "omega"],
    "differential_firstorder": ["v_ref", "omega"],
    "ackermann":    ["speed", "steer"],
}

# Velocidade real (lida do estado do robô após o step)
# Mapeamento: campo_no_frame → chave_no_robot_state
_ROBOT_REAL_MAP = {
    "holonomic":    {"vx_real": "vx",    "vy_real": "vy"},
    "differential": {"v_real":  "v",     "omega_real": "omega"},
    "differential_firstorder": {"v_real": "v", "omega_real": "omega"},
    "ackermann":    {"speed_real": "speed", "steer_real": "steer"},
}

_ROBOT_TYPE_ALIASES = {
    "omni": "holonomic", "omnidirectional": "holonomic",
    "diff": "differential", "unicycle": "differential", "differential_firstorder": "differential_firstorder", "firstorder": "differential_firstorder", "diff_tau": "differential_firstorder",
    "nonholonomic": "differential",
    "car": "ackermann", "racecar": "ackermann",
}

_COMMON_FIELDS = ["t", "x", "y", "theta"]


# ──────────────────────────────────────────────────────────────
# Frame — uma amostra no tempo
# ──────────────────────────────────────────────────────────────

@dataclass
class Frame:
    """Uma amostra do simulador em um instante t."""

    t:      float
    x:      float
    y:      float
    theta:  float

    # ── ação de controle (saída do controller) ─────────────────
    vx:     float | None = None   # holonomic
    vy:     float | None = None   # holonomic
    v:      float | None = None   # differential
    omega:  float | None = None   # differential
    speed:  float | None = None   # ackermann
    steer:  float | None = None   # ackermann
    v_ref:      float | None = None   # differential_firstorder
    omega_ref:  float | None = None   # differential

    # ── velocidade real (lida do robot.state() após step()) ────
    vx_real:    float | None = None   # holonomic
    vy_real:    float | None = None   # holonomic
    v_real:     float | None = None   # differential
    omega_real: float | None = None   # differential
    speed_real: float | None = None   # ackermann
    steer_real: float | None = None   # ackermann

    # ── planejamento ───────────────────────────────────────────
    goal:       tuple | None = None   # (x, y) ou (x, y, theta)
    waypoint:   tuple | None = None   # waypoint atual do planner
    wp_index:   int   | None = None   # índice do waypoint atual

    # ── segmento de gravação ───────────────────────────────────
    segment:    int          = 0


# ──────────────────────────────────────────────────────────────
# SimLog — container do log completo
# ──────────────────────────────────────────────────────────────

@dataclass
class SimLog:
    """Container salvo em pickle com todos os frames da simulação."""

    robot_type:    str
    frames:        list[Frame]        = field(default_factory=list)
    planned_path:  list[tuple] | None = None
    planned_curve: dict        | None = None

    def to_numpy(self) -> dict[str, np.ndarray]:
        """Converte frames para dicionário de arrays numpy."""
        if not self.frames:
            return {}

        def _get(attr):
            return np.array([getattr(f, attr) for f in self.frames], dtype=float)

        def _get_nullable(attr):
            return np.array(
                [float(v) if (v := getattr(f, attr)) is not None else np.nan
                 for f in self.frames], dtype=float,
            )

        result = {
            "t":       _get("t"),
            "x":       _get("x"),
            "y":       _get("y"),
            "theta":   _get("theta"),
            "segment": np.array([f.segment for f in self.frames], dtype=int),
        }

        # ação de controle
        for cmd in _ROBOT_CMD_FIELDS.get(self.robot_type, []):
            print(cmd)
            result[cmd] = _get_nullable(cmd)

        # velocidade real
        for real_key in _ROBOT_REAL_MAP.get(self.robot_type, {}):
            # print(f"Mapping real field '{real_key}' for robot type '{self.robot_type}'")
            result[real_key] = _get_nullable(real_key)
        # print(result.keys())
        # goal
        goals = [f.goal for f in self.frames]
        if any(g is not None for g in goals):
            result["goal_x"] = np.array([g[0] if g is not None else np.nan for g in goals])
            result["goal_y"] = np.array([g[1] if g is not None else np.nan for g in goals])
            if any(len(g) > 2 for g in goals if g is not None):
                result["goal_theta"] = np.array(
                    [g[2] if (g is not None and len(g) > 2) else np.nan for g in goals]
                )

        # waypoint atual
        wps = [f.waypoint for f in self.frames]
        if any(w is not None for w in wps):
            result["wp_x"] = np.array([w[0] if w is not None else np.nan for w in wps])
            result["wp_y"] = np.array([w[1] if w is not None else np.nan for w in wps])

        # índice do waypoint
        wp_idx = [f.wp_index for f in self.frames]
        if any(i is not None for i in wp_idx):
            result["wp_index"] = np.array(
                [i if i is not None else -1 for i in wp_idx], dtype=int
            )

        return result

    def segments(self) -> dict[int, list[Frame]]:
        segs: dict[int, list[Frame]] = {}
        for f in self.frames:
            segs.setdefault(f.segment, []).append(f)
        return segs

    def plot_log(self):
        _plot_log(self)


# ──────────────────────────────────────────────────────────────
# DataLogger
# ──────────────────────────────────────────────────────────────

class DataLogger:
    """
    Registra estado + comando + velocidade real a cada frame via draw_callback.

    - Grava apenas quando há waypoints ativos.
    - Cria novo segmento quando novos waypoints são adicionados.
    - Suporta caminho planejado (waypoints ou curva paramétrica).
    """

    def __init__(self, max_samples: int | None = None):
        self.max_samples    = max_samples
        self._t             = 0.0
        self._log: SimLog | None = None
        self._recording     = False
        self._segment_idx   = -1
        self._last_wp_count = 0

    # ── inicialização lazy ─────────────────────────────────────

    def _init(self, robot):
        state = robot.state()
        rtype = state.get("type", "differential").lower()
        rtype = _ROBOT_TYPE_ALIASES.get(rtype, rtype)
        self._log = SimLog(robot_type=rtype)

    # ── reset ──────────────────────────────────────────────────

    def reset(self):
        """Descarta frames e reseta estado de gravação."""
        robot_type = self._log.robot_type if self._log else None
        self._t             = 0.0
        self._recording     = False
        self._segment_idx   = -1
        self._last_wp_count = 0
        self._log = SimLog(robot_type=robot_type) if robot_type else None
        print("[DataLogger] Logger reiniciado.")

    # ── detecção de waypoints ──────────────────────────────────

    def _waypoint_state(self, sim) -> tuple[bool, int]:
        try:
            wm = sim.waypoints
            return wm.has_waypoint(), len(wm.waypoints)
        except Exception:
            return False, 0

    # ── extração de goal e waypoint ───────────────────────────

    @staticmethod
    def _extract_goal(sim) -> tuple | None:
        try:
            g = sim.waypoints.get_current_waypoint()
            return tuple(float(v) for v in g) if g is not None else None
        except Exception:
            return None

    @staticmethod
    def _extract_waypoint_info(sim) -> tuple[tuple | None, int | None]:
        ctrl      = getattr(sim, "controller", None)
        waypoints = getattr(ctrl, "_waypoints", None)
        wp_idx    = getattr(ctrl, "_wp_idx",    None)
        if not waypoints or wp_idx is None:
            return None, None
        if wp_idx < len(waypoints):
            return tuple(float(v) for v in waypoints[wp_idx]), int(wp_idx)
        return None, int(wp_idx)

    # ── record ─────────────────────────────────────────────────

    def _record(self, sim):
        if self.max_samples and len(self._log.frames) >= self.max_samples:
            return

        robot  = sim.robot
        self._t += sim.dt
        state  = robot.state()
        rtype  = self._log.robot_type

        # ação de controle (o que o controller pediu)
        cmd_fields = {
            f: float(state.get(f, 0.0))
            for f in _ROBOT_CMD_FIELDS.get(rtype, [])
        }

        # velocidade real (o que o robô executou após saturação/cinemática)
        real_fields = {
            real_key: float(state.get(state_key, 0.0))
            for real_key, state_key in _ROBOT_REAL_MAP.get(rtype, {}).items()
        }

        goal           = self._extract_goal(sim)
        waypoint, wp_i = self._extract_waypoint_info(sim)

        self._log.frames.append(Frame(
            t=self._t,
            x=float(robot.x),
            y=float(robot.y),
            theta=float(robot.theta),
            goal=goal,
            waypoint=waypoint,
            wp_index=wp_i,
            segment=self._segment_idx,
            **cmd_fields,
            **real_fields,
        ))

    # ── draw_callback ──────────────────────────────────────────

    def draw_callback(self, sim, screen):
        if not sim.running_simulation:
            return

        if self._log is None:
            self._init(sim.robot)

        has_active, total_wp = self._waypoint_state(sim)

        # Novos waypoints → novo segmento
        if total_wp > self._last_wp_count and has_active:
            self._segment_idx += 1
            self._recording    = True
            print(f"[DataLogger] Segmento {self._segment_idx} iniciado "
                  f"({len(self._log.frames)} frames, {total_wp} waypoints).")

        self._last_wp_count = total_wp

        # Sem waypoints ativos → pausa
        if not has_active:
            if self._recording:
                print(f"[DataLogger] Segmento {self._segment_idx} concluído "
                      f"— {len(self._log.frames)} frames totais.")
            self._recording = False
            return

        if self._recording:
            self._record(sim)

    # ── caminho planejado ──────────────────────────────────────

    def set_planned_path(self, path: list[tuple]):
        """Registra caminho planejado como lista de (x,y) ou (x,y,theta)."""
        if self._log is None:
            print("[DataLogger] Não inicializado.")
            return
        self._log.planned_path = [tuple(float(v) for v in p) for p in path]
        print(f"[DataLogger] Caminho planejado: {len(path)} pontos.")

    def set_planned_curve(self, t, x, y, theta=None):
        """Registra caminho planejado como curva paramétrica."""
        if self._log is None:
            print("[DataLogger] Não inicializado.")
            return
        curve = {
            "t": np.array(t, dtype=float),
            "x": np.array(x, dtype=float),
            "y": np.array(y, dtype=float),
        }
        if theta is not None:
            curve["theta"] = np.array(theta, dtype=float)
        self._log.planned_curve = curve
        print(f"[DataLogger] Curva planejada: {len(curve['x'])} pontos.")

    # ── exportação ─────────────────────────────────────────────

    def save(self, path: str = "log.pkl"):
        if self._log is None or not self._log.frames:
            print("[DataLogger] Nenhum dado para salvar.")
            return
        with open(path, "wb") as f:
            pickle.dump(self._log, f)
        print(f"[DataLogger] {len(self._log.frames)} frames / "
              f"{self._segment_idx + 1} segmento(s) → '{path}'")

    @staticmethod
    def load(path: str) -> SimLog:
        with open(path, "rb") as f:
            log = pickle.load(f)
        print(f"[DataLogger] '{path}': {len(log.frames)} frames, tipo={log.robot_type}")
        return log

    # ── plot ───────────────────────────────────────────────────

    def plot(self):
        if self._log is None or not self._log.frames:
            print("[DataLogger] Nenhum dado para plotar.")
            return
        _plot_log(self._log)


# ──────────────────────────────────────────────────────────────
# Helpers de plot
# ──────────────────────────────────────────────────────────────

def _safe_legend(ax, **kwargs):
    """Só chama legend() se houver artistas com label — evita UserWarning."""
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(handles, labels, **kwargs)


def _plot_log(log: SimLog):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    h     = log.to_numpy()
    t     = h["t"]
    rtype = log.robot_type
    segs  = np.unique(h["segment"])
    cmap  = cm.get_cmap("tab10", max(len(segs), 1))

    fig, axes = plt.subplots(3, 3, figsize=(18, 12))
    # fig.suptitle(
        # f"SimLog — {rtype}  |  {len(log.frames)} frames  |  {len(segs)} segmento(s)",
        # fontsize=10,
    # )

    # ── [0,0] Trajetória XY ────────────────────────────────────
    ax = axes[0, 0]
    for i, seg in enumerate(segs):
        mask = h["segment"] == seg
        ax.plot(h["x"][mask], h["y"][mask], color=cmap(i), lw=1.5, label=f"seg {seg}")
    if log.planned_path:
        px = [p[0] for p in log.planned_path]
        py = [p[1] for p in log.planned_path]
        ax.plot(px, py, "--", color="gray", lw=1.5, alpha=0.8, label="planejado")
        ax.scatter(px, py, s=20, color="gray", alpha=0.6, zorder=4)
    if log.planned_curve:
        ax.plot(log.planned_curve["x"], log.planned_curve["y"],
                "--", color="purple", lw=1.5, alpha=0.8, label="curva planejada")
    if "goal_x" in h:
        ax.scatter(h["goal_x"], h["goal_y"], s=60, c="red", zorder=5, label="goal")
    if "wp_x" in h:
        ax.scatter(h["wp_x"], h["wp_y"], s=12, c="orange", alpha=0.3, zorder=3,
                   label="waypoint atual")
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)")
    ax.set_title("Trajetória", fontsize=11); ax.axis("equal"); ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [0,1] Orientação ───────────────────────────────────────
    ax = axes[0, 1]
    for i, seg in enumerate(segs):
        mask = h["segment"] == seg
        ax.plot(t[mask], np.degrees(h["theta"][mask]), color=cmap(i), label=f"seg {seg}")
    if "goal_theta" in h:
        ax.plot(t, np.degrees(h["goal_theta"]), "--", color="gray",
                alpha=0.6, label="θ desejado")
    if log.planned_curve and "theta" in log.planned_curve:
        tc = np.linspace(t[0], t[-1], len(log.planned_curve["theta"]))
        ax.plot(tc, np.degrees(log.planned_curve["theta"]),
                "--", color="purple", alpha=0.6, label="θ planejado")
    ax.set_xlabel("t (s)"); ax.set_ylabel("θ (°)")
    ax.set_title("Orientação", fontsize=11); ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [0,2] Distância ao goal ────────────────────────────────
    ax = axes[0, 2]
    if "goal_x" in h:
        rho = np.hypot(h["x"] - h["goal_x"], h["y"] - h["goal_y"])
        for i, seg in enumerate(segs):
            mask = h["segment"] == seg
            ax.plot(t[mask], rho[mask], color=cmap(i), label=f"seg {seg}")
        ax.set_ylabel("ρ (m)"); ax.set_title("Distância ao goal", fontsize=11)
    else:
        ax.set_title("Distância ao goal\n(sem goal registrado)", fontsize=11)
    ax.set_xlabel("t (s)"); ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [1,0] Velocidade linear: cmd vs real ───────────────────
    ax = axes[1, 0]
    for i, seg in enumerate(segs):
        mask = h["segment"] == seg
        c = cmap(i)
        if rtype == "holonomic":
            cmd  = np.hypot(h.get("vx",      np.zeros_like(t)),
                            h.get("vy",      np.zeros_like(t)))
            real = np.hypot(h.get("vx_real", np.zeros_like(t)),
                            h.get("vy_real", np.zeros_like(t)))
            lbl = f"s{seg}"
            ax.plot(t[mask], cmd[mask],  color=c, lw=1.5, label=f"cmd {lbl}")
            ax.plot(t[mask], real[mask], color=c, lw=1.0, ls="--",
                    alpha=0.7, label=f"real {lbl}")
            ax.set_ylabel("|v| (m/s)")
        elif rtype == "differential":
            lbl = f"s{seg}"
            ax.plot(t[mask], h["v"][mask],      color=c, lw=1.5, label=f"cmd {lbl}")
            ax.plot(t[mask], h["v_real"][mask], color=c, lw=1.0, ls="--",
                    alpha=0.7, label=f"real {lbl}")
            ax.set_ylabel("v (m/s)")
        elif rtype == "differential_firstorder":
            lbl = f"s{seg}"
            ax.plot(t[mask], h["v_ref"][mask],      color=c, lw=1.5, label=f"cmd {lbl}")
            ax.plot(t[mask], h["v_real"][mask], color=c, lw=1.0, ls="--",
                    alpha=0.7, label=f"real {lbl}")
            ax.set_ylabel("v (m/s)")
        else:
            lbl = f"s{seg}"
            ax.plot(t[mask], h["speed"][mask],      color=c, lw=1.5, label=f"cmd {lbl}")
            ax.plot(t[mask], h["speed_real"][mask], color=c, lw=1.0, ls="--",
                    alpha=0.7, label=f"real {lbl}")
            ax.set_ylabel("speed (m/s)")
    ax.set_xlabel("t (s)")
    ax.set_title("Vel. linear  (— cmd  ╌ real)", fontsize=11)
    ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [1,1] Velocidade angular / steer: cmd vs real ──────────
    ax = axes[1, 1]
    for i, seg in enumerate(segs):
        mask = h["segment"] == seg
        c = cmap(i)
        lbl = f"s{seg}"
        if rtype == "holonomic":
            ax.plot(t[mask], h.get("vx",      np.zeros_like(t))[mask],
                    color=c, lw=1.5, label=f"vx cmd {lbl}")
            ax.plot(t[mask], h.get("vx_real", np.zeros_like(t))[mask],
                    color=c, lw=1.0, ls="--", alpha=0.7, label=f"vx real {lbl}")
            ax.plot(t[mask], h.get("vy",      np.zeros_like(t))[mask],
                    color=c, lw=1.5, ls=":", label=f"vy cmd {lbl}")
            ax.plot(t[mask], h.get("vy_real", np.zeros_like(t))[mask],
                    color=c, lw=1.0, ls="-.", alpha=0.7, label=f"vy real {lbl}")
            ax.set_ylabel("m/s"); ax.set_title("vx / vy  (— cmd  ╌ real)", fontsize=11)
        elif rtype == "differential":
            ax.plot(t[mask], np.degrees(h["omega"][mask]),
                    color=c, lw=1.5, label=f"cmd {lbl}")
            ax.plot(t[mask], np.degrees(h["omega_real"][mask]),
                    color=c, lw=1.0, ls="--", alpha=0.7, label=f"real {lbl}")
            ax.set_ylabel("ω (°/s)")
            ax.set_title("Vel. angular  (— cmd  ╌ real)", fontsize=11)
        elif rtype == "differential_firstorder":
            ax.plot(t[mask], np.degrees(h["omega"][mask]),
                    color=c, lw=1.5, label=f"cmd {lbl}")
            ax.plot(t[mask], np.degrees(h["omega_real"][mask]),
                    color=c, lw=1.0, ls="--", alpha=0.7, label=f"real {lbl}")
            ax.set_ylabel("ω (°/s)")
            ax.set_title("Vel. angular  (— cmd  ╌ real)", fontsize=11)
        else:
            ax.plot(t[mask], np.degrees(h["steer"][mask]),
                    color=c, lw=1.5, label=f"cmd {lbl}")
            ax.plot(t[mask], np.degrees(h["steer_real"][mask]),
                    color=c, lw=1.0, ls="--", alpha=0.7, label=f"real {lbl}")
            ax.set_ylabel("steer (°)")
            ax.set_title("Esterçamento  (— cmd  ╌ real)", fontsize=11)
    ax.set_xlabel("t (s)"); ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [1,2] Waypoint index ───────────────────────────────────
    ax = axes[1, 2]
    if "wp_index" in h:
        for i, seg in enumerate(segs):
            mask = h["segment"] == seg
            ax.step(t[mask], h["wp_index"][mask], where="post",
                    color=cmap(i), label=f"seg {seg}")
        ax.set_ylabel("índice"); ax.set_title("Waypoint atual", fontsize=11)
    else:
        ax.set_title("Waypoint (sem planner conectado)", fontsize=11)
    ax.set_xlabel("t (s)"); ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [2,0] Erro de posição por segmento ─────────────────────
    ax = axes[2, 0]
    if "goal_x" in h:
        rho = np.hypot(h["x"] - h["goal_x"], h["y"] - h["goal_y"])
        for i, seg in enumerate(segs):
            mask = h["segment"] == seg
            ax.fill_between(t[mask], rho[mask], alpha=0.3, color=cmap(i))
            ax.plot(t[mask], rho[mask], color=cmap(i), lw=1.0, label=f"seg {seg}")
        ax.set_ylabel("ρ (m)"); ax.set_title("Erro de posição (área)", fontsize=11)
    else:
        ax.set_title("Erro de posição\n(sem goal registrado)", fontsize=11)
    ax.set_xlabel("t (s)"); ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [2,1] Diferença cmd - real (velocidade linear) ─────────
    ax = axes[2, 1]
    for i, seg in enumerate(segs):
        mask = h["segment"] == seg
        c = cmap(i)
        if rtype == "holonomic":
            cmd  = np.hypot(h.get("vx",      np.zeros_like(t)),
                            h.get("vy",      np.zeros_like(t)))
            real = np.hypot(h.get("vx_real", np.zeros_like(t)),
                            h.get("vy_real", np.zeros_like(t)))
            ax.plot(t[mask], (cmd - real)[mask], color=c, lw=1.0, label=f"seg {seg}")
            ax.set_ylabel("Δ|v| (m/s)")
        elif rtype == "differential":
            ax.plot(t[mask], (h["v"] - h["v_real"])[mask],
                    color=c, lw=1.0, label=f"seg {seg}")
            ax.set_ylabel("Δv (m/s)")        
        elif rtype == "differential_firstorder":
            ax.plot(t[mask], (h["v_ref"] - h["v_real"])[mask],
                    color=c, lw=1.0, label=f"seg {seg}")
            ax.set_ylabel("Δv (m/s)")        
        else:
            ax.plot(t[mask], (h["speed"] - h["speed_real"])[mask],
                    color=c, lw=1.0, label=f"seg {seg}")
            ax.set_ylabel("Δspeed (m/s)")
    ax.axhline(0, color="black", lw=0.8, ls="--")
    ax.set_xlabel("t (s)"); ax.set_title("Diferença cmd − real (vel. linear)", fontsize=11)
    ax.grid(True)
    _safe_legend(ax, fontsize=7)

    # ── [2,2] Diferença cmd - real (angular / steer) ───────────
    ax = axes[2, 2]
    for i, seg in enumerate(segs):
        mask = h["segment"] == seg
        c = cmap(i)
        if rtype == "holonomic":
            # norma do erro em (vx,vy) separado
            dvx = (h.get("vx", np.zeros_like(t)) -
                   h.get("vx_real", np.zeros_like(t)))
            dvy = (h.get("vy", np.zeros_like(t)) -
                   h.get("vy_real", np.zeros_like(t)))
            ax.plot(t[mask], dvx[mask], color=c, lw=1.0, label=f"Δvx s{seg}")
            ax.plot(t[mask], dvy[mask], color=c, lw=1.0, ls="--",
                    alpha=0.7, label=f"Δvy s{seg}")
            ax.set_ylabel("Δv (m/s)")
            ax.set_title("Diferença cmd − real (vx, vy)", fontsize=11)
        elif rtype == "differential" or rtype == "differential_firstorder":
            ax.plot(t[mask],
                    np.degrees(h["omega"] - h["omega_real"])[mask],
                    color=c, lw=1.0, label=f"seg {seg}")
            ax.set_ylabel("Δω (°/s)")
            ax.set_title("Diferença cmd − real (vel. angular)", fontsize=11)
        else:
            ax.plot(t[mask],
                    np.degrees(h["steer"] - h["steer_real"])[mask],
                    color=c, lw=1.0, label=f"seg {seg}")
            ax.set_ylabel("Δsteer (°)")
            ax.set_title("Diferença cmd − real (esterçamento)", fontsize=11)
    ax.axhline(0, color="black", lw=0.8, ls="--")
    ax.set_xlabel("t (s)"); ax.grid(True)
    _safe_legend(ax, fontsize=7)

    plt.tight_layout()
    plt.show()