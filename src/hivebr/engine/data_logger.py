"""
data_logger.py
--------------
DataLogger genérico para hivebr.engine.

Registra o estado de **todos os robôs presentes na arena** a cada frame,
via ``draw_callback``. Suporta janelas de plot interativas (Tk + Matplotlib)
e exportação em ``pickle`` e ``csv``.

Comportamento de gravação
-------------------------
- Gravação ativa enquanto ``sim.running_simulation`` for verdadeiro.
- Cada robô possui o seu próprio log e a sua própria sequência de segmentos.
- Um novo segmento é iniciado sempre que novos waypoints são adicionados
  àquele robô.
- Cada segmento é identificado pelo campo ``segment`` nos frames.

Uso
---
    from hivebr.engine.data_logger import DataLogger

    logger = DataLogger()
    sim    = Simulator(controller=ctrl)
    sim.run()

    logger.save("run_01.pkl")     # pickle
    logger.save_csv("run_01.csv") # csv
    logger.plot()                 # janela interativa de plot

    # Carregar e plotar depois
    log = DataLogger.load("run_01.pkl")
    log.plot_log()
"""

from __future__ import annotations

import csv
import pickle
from collections import OrderedDict
from dataclasses import dataclass, field

import numpy as np


# ──────────────────────────────────────────────────────────────
# Campos por tipo de robô
# ──────────────────────────────────────────────────────────────

# Ação de controle (saída do controller, antes do step)
_ROBOT_CMD_FIELDS = {
    "holonomic":    ["vx", "vy"],
    "differential": ["v", "omega"],
    "differential_firstorder": ["v_ref", "omega"],
    "ackermann":    ["speed", "steer"],
    "boat":         ["v", "omega"],
}

# Velocidade real (lida do estado do robô após o step)
# Mapeamento: campo_no_frame -> chave_no_robot_state
_ROBOT_REAL_MAP = {
    "holonomic":    {"vx_real": "vx",    "vy_real": "vy"},
    "differential": {"v_real":  "v",     "omega_real": "omega"},
    "differential_firstorder": {"v_real": "v", "omega_real": "omega"},
    "ackermann":    {"speed_real": "speed", "steer_real": "steer"},
    "boat":         {"v_real": "v", "omega_real": "omega"},
}

# Mapeamento: campo_no_frame (comando) -> chave no dict de comando do controller
_ROBOT_CMD_KEYS = {
    "holonomic":    {"vx": "vx", "vy": "vy"},
    "differential": {"v": "v", "omega": "omega"},
    "differential_firstorder": {"v_ref": "v", "omega": "omega"},
    "ackermann":    {"speed": "speed", "steer": "steer"},
    "boat":         {"v": "v", "omega": "omega"},
}

_ROBOT_TYPE_ALIASES = {
    "omni": "holonomic", "omnidirectional": "holonomic",
    "diff": "differential", "unicycle": "differential",
    "differential_firstorder": "differential_firstorder",
    "firstorder": "differential_firstorder", "diff_tau": "differential_firstorder",
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
# SimLog — container do log de um único robô
# ──────────────────────────────────────────────────────────────

@dataclass
class SimLog:
    """Container com todos os frames de um robô."""

    robot_type:    str
    frames:        list[Frame]        = field(default_factory=list)
    planned_path:  list[tuple] | None = None
    planned_curve: dict        | None = None
    robot_index:   int                = 0
    label:         str                = ""

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
            result[cmd] = _get_nullable(cmd)

        # velocidade real
        for real_key in _ROBOT_REAL_MAP.get(self.robot_type, {}):
            result[real_key] = _get_nullable(real_key)

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
        from .plot_window import show_interactive_plot
        index = getattr(self, "robot_index", 0)
        show_interactive_plot(MultiRobotLog(logs=OrderedDict([(index, self)])))


# ──────────────────────────────────────────────────────────────
# MultiRobotLog — container de vários robôs
# ──────────────────────────────────────────────────────────────

@dataclass
class MultiRobotLog:
    """Container com os logs de todos os robôs de uma simulação."""

    logs: dict = field(default_factory=dict)   # {robot_index: SimLog}

    # ── compatibilidade com a API antiga (robô único) ──────────

    @property
    def robot_type(self):
        for log in self.logs.values():
            return log.robot_type
        return None

    @property
    def frames(self) -> list[Frame]:
        return [f for log in self.logs.values() for f in log.frames]

    @property
    def planned_path(self):
        for log in self.logs.values():
            if log.planned_path:
                return log.planned_path
        return None

    @property
    def planned_curve(self):
        for log in self.logs.values():
            if log.planned_curve:
                return log.planned_curve
        return None

    def __bool__(self) -> bool:
        return any(log.frames for log in self.logs.values())

    def to_numpy(self) -> dict[int, dict[str, np.ndarray]]:
        return {i: log.to_numpy() for i, log in self.logs.items()}

    def segments(self) -> dict[int, dict[int, list[Frame]]]:
        return {i: log.segments() for i, log in self.logs.items()}

    def plot_log(self):
        from .plot_window import show_interactive_plot
        show_interactive_plot(self)


# ──────────────────────────────────────────────────────────────
# DataLogger
# ──────────────────────────────────────────────────────────────

class DataLogger:
    """
    Registra estado + comando + velocidade real de cada robô a cada frame
    via ``draw_callback``.

    A gravação ocorre enquanto ``sim.running_simulation`` for verdadeiro.
    Cada robô tem o seu próprio :class:`SimLog` e a sua própria sequência
    de segmentos (novo segmento a cada waypoint adicionado).
    """

    def __init__(self, max_samples: int | None = None):
        self.max_samples = max_samples
        self._t = 0.0
        self._logs: "OrderedDict[int, SimLog]" = OrderedDict()
        self._segment_idx: dict[int, int] = {}
        self._last_wp_count: dict[int, int] = {}
        self._initialized = False

    # ── inicialização lazy ─────────────────────────────────────

    def _init(self, sim):
        for i, robot in enumerate(sim.robots):
            try:
                rtype = str(robot.state().get("type", "differential")).lower()
            except Exception:
                rtype = "differential"
            rtype = _ROBOT_TYPE_ALIASES.get(rtype, rtype)
            self._logs[i] = SimLog(
                robot_type=rtype, robot_index=i, label=f"B-Bot{i}"
            )
            self._segment_idx[i] = -1
            self._last_wp_count[i] = 0
        self._initialized = True

    # ── reset ──────────────────────────────────────────────────

    def reset(self):
        """Descarta frames e reseta estado de gravação."""
        self._t = 0.0
        self._logs = OrderedDict()
        self._segment_idx = {}
        self._last_wp_count = {}
        self._initialized = False
        print("[DataLogger] Logger reiniciado.")

    # ── detecção de waypoints ──────────────────────────────────

    @staticmethod
    def _waypoint_manager(sim, index):
        managers = getattr(sim, "waypoint_managers", None)
        if managers is not None and index < len(managers):
            return managers[index]
        return getattr(sim, "waypoints", None)

    def _waypoint_state(self, sim, index) -> tuple[bool, int]:
        try:
            wm = self._waypoint_manager(sim, index)
            return wm.has_waypoint(), len(wm.waypoints)
        except Exception:
            return False, 0

    # ── extração de goal e waypoint ───────────────────────────

    @staticmethod
    def _extract_goal(wm) -> tuple | None:
        try:
            g = wm.get_current_waypoint() if wm is not None else None
            return tuple(float(v) for v in g) if g is not None else None
        except Exception:
            return None

    @staticmethod
    def _extract_waypoint_info(wm) -> tuple[tuple | None, int | None]:
        try:
            if wm is None:
                return None, None
            goal = wm.get_current_waypoint()
            waypoint = tuple(float(v) for v in goal[:2]) if goal is not None else None
            return waypoint, int(wm.current_index)
        except Exception:
            return None, None

    # ── record ─────────────────────────────────────────────────

    def _record(self, sim, index, wm):
        log = self._logs[index]
        if self.max_samples and len(log.frames) >= self.max_samples:
            return

        robot = sim.robots[index]
        state = robot.state()
        rtype = log.robot_type

        # ação de controle (o que o controller pediu, antes do ruído)
        last_cmds = getattr(sim, "last_commands", None)
        raw_cmd = (last_cmds[index]
                   if last_cmds is not None and index < len(last_cmds) else None)
        cmd_keys = _ROBOT_CMD_KEYS.get(rtype, {})
        if raw_cmd is not None:
            cmd_fields = {
                field: float(raw_cmd.get(key, 0.0))
                for field, key in cmd_keys.items()
            }
        else:
            cmd_fields = {
                f: float(state.get(f, 0.0))
                for f in _ROBOT_CMD_FIELDS.get(rtype, [])
            }

        # velocidade real (o que o robô executou após saturação/cinemática)
        real_fields = {
            real_key: float(state.get(state_key, 0.0))
            for real_key, state_key in _ROBOT_REAL_MAP.get(rtype, {}).items()
        }

        goal = self._extract_goal(wm)
        waypoint, wp_i = self._extract_waypoint_info(wm)

        log.frames.append(Frame(
            t=self._t,
            x=float(robot.x),
            y=float(robot.y),
            theta=float(robot.theta),
            goal=goal,
            waypoint=waypoint,
            wp_index=wp_i,
            segment=self._segment_idx[index],
            **cmd_fields,
            **real_fields,
        ))

    # ── draw_callback ──────────────────────────────────────────

    def draw_callback(self, sim, screen):
        if not sim.running_simulation:
            return

        if not self._initialized:
            self._init(sim)

        self._t += sim.dt

        for index in range(len(sim.robots)):
            _, total_wp = self._waypoint_state(sim, index)

            # Novos waypoints -> novo segmento
            if total_wp > self._last_wp_count.get(index, 0):
                self._segment_idx[index] = self._segment_idx.get(index, -1) + 1
                print(f"[DataLogger] B-Bot{index} — segmento "
                      f"{self._segment_idx[index]} iniciado "
                      f"({len(self._logs[index].frames)} frames, "
                      f"{total_wp} waypoints).")

            self._last_wp_count[index] = total_wp
            self._record(sim, index, self._waypoint_manager(sim, index))

    # ── caminho planejado ──────────────────────────────────────

    def set_planned_path(self, path: list[tuple], robot_index: int = 0):
        """Registra caminho planejado de um robô como lista de (x,y[,theta])."""
        if robot_index not in self._logs:
            print(f"[DataLogger] Robô {robot_index} não inicializado.")
            return
        self._logs[robot_index].planned_path = [
            tuple(float(v) for v in p) for p in path
        ]
        print(f"[DataLogger] Caminho planejado (B-Bot{robot_index}): "
              f"{len(path)} pontos.")

    def set_planned_curve(self, t, x, y, theta=None, robot_index: int = 0):
        """Registra caminho planejado de um robô como curva paramétrica."""
        if robot_index not in self._logs:
            print(f"[DataLogger] Robô {robot_index} não inicializado.")
            return
        curve = {
            "t": np.array(t, dtype=float),
            "x": np.array(x, dtype=float),
            "y": np.array(y, dtype=float),
        }
        if theta is not None:
            curve["theta"] = np.array(theta, dtype=float)
        self._logs[robot_index].planned_curve = curve
        print(f"[DataLogger] Curva planejada (B-Bot{robot_index}): "
              f"{len(curve['x'])} pontos.")

    # ── exportação ─────────────────────────────────────────────

    def result(self) -> MultiRobotLog:
        return MultiRobotLog(logs=self._logs)

    def _has_data(self) -> bool:
        return bool(self._logs) and any(l.frames for l in self._logs.values())

    def save(self, path: str = "log.pkl"):
        """Salva o log completo em pickle."""
        if not self._has_data():
            print("[DataLogger] Nenhum dado para salvar.")
            return
        with open(path, "wb") as f:
            pickle.dump(self.result(), f)
        total = sum(len(l.frames) for l in self._logs.values())
        print(f"[DataLogger] {total} frames / {len(self._logs)} robô(s) -> '{path}'")

    def save_csv(self, path: str = "log.csv"):
        """Salva o log completo em CSV (uma linha por robô por frame)."""
        if not self._has_data():
            print("[DataLogger] Nenhum dado para salvar.")
            return

        columns = ["robot", "robot_type", "segment", "t", "x", "y", "theta"]
        arrays: "OrderedDict[int, dict]" = OrderedDict()
        for index in sorted(self._logs):
            arr = self._logs[index].to_numpy()
            arrays[index] = arr
            for key in arr:
                if key not in columns:
                    columns.append(key)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for index, arr in arrays.items():
                log = self._logs[index]
                for row in range(len(log.frames)):
                    writer.writerow([
                        index if col == "robot"
                        else log.robot_type if col == "robot_type"
                        else arr[col][row] if col in arr
                        else ""
                        for col in columns
                    ])

        total = sum(len(l.frames) for l in self._logs.values())
        print(f"[DataLogger] {total} frames / {len(self._logs)} robô(s) -> '{path}'")

    def export(self, path: str):
        """Exporta escolhendo o formato pela extensão (.csv ou .pkl)."""
        if str(path).lower().endswith(".csv"):
            self.save_csv(path)
        else:
            self.save(path)

    @staticmethod
    def load(path: str):
        with open(path, "rb") as f:
            log = pickle.load(f)
        if isinstance(log, MultiRobotLog):
            total = sum(len(l.frames) for l in log.logs.values())
            print(f"[DataLogger] '{path}': {total} frames, "
                  f"{len(log.logs)} robô(s)")
        else:
            print(f"[DataLogger] '{path}': {len(log.frames)} frames, "
                  f"tipo={log.robot_type}")
        return log

    # ── plot ───────────────────────────────────────────────────

    def plot(self):
        if not self._has_data():
            print("[DataLogger] Nenhum dado para plotar.")
            return
        from .plot_window import show_interactive_plot
        show_interactive_plot(self.result())
