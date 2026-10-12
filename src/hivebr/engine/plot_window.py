"""
plot_window.py
--------------
Janela de plot interativa (Tkinter + Matplotlib) para inspecionar os dados
registrados pelo :class:`~hivebr.engine.data_logger.DataLogger`.

A janela permite:

- selecionar um ou **vários** robôs da arena;
- selecionar os sinais a exibir a partir de uma lista (trajetória XY,
  erro de posição, erro de orientação, velocidades linear/angular
  comando vs real, comandos de controle, etc.);
- escolher a grade de subplots (1x1, 2x1, 2x2, ...);
- sobrepor vários robôs no mesmo subplot ou separar um robô por subplot;
- salvar a figura corrente (png/pdf/svg).

A janela é aberta por :func:`show_interactive_plot`, normalmente a partir do
botão **Plot Log** do simulador ou de ``DataLogger.plot()``.
"""

from __future__ import annotations

import os

import numpy as np

from .data_logger import _ROBOT_CMD_FIELDS, MultiRobotLog


# ──────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────

def _wrap_to_pi(a):
    return (a + np.pi) % (2.0 * np.pi) - np.pi


def _has_finite(arr) -> bool:
    return arr is not None and np.any(np.isfinite(arr))


def _xy_error(data):
    if "goal_x" not in data or "goal_y" not in data:
        return None
    rho = np.hypot(data["x"] - data["goal_x"], data["y"] - data["goal_y"])
    return rho if _has_finite(rho) else None


def _theta_error(data):
    if "goal_theta" not in data:
        return None
    err = _wrap_to_pi(data["theta"] - data["goal_theta"])
    return err if _has_finite(err) else None


def _linear_pair(data, robot_type):
    """Retorna (cmd, real, ylabel) da velocidade linear."""
    if robot_type == "holonomic":
        cmd = np.hypot(data.get("vx", 0.0), data.get("vy", 0.0))
        real = np.hypot(data.get("vx_real", 0.0), data.get("vy_real", 0.0))
        return cmd, real, "|v| (m/s)"
    if robot_type == "ackermann":
        return data.get("speed"), data.get("speed_real"), "speed (m/s)"
    if robot_type == "differential_firstorder":
        return data.get("v_ref"), data.get("v_real"), "v (m/s)"
    return data.get("v"), data.get("v_real"), "v (m/s)"


def _angular_pair(data, robot_type):
    """Retorna (cmd, real, ylabel, in_degrees)."""
    if robot_type == "holonomic":
        return data.get("vx"), data.get("vx_real"), "vx (m/s)", False
    if robot_type == "ackermann":
        return data.get("steer"), data.get("steer_real"), "δ (°)", True
    return data.get("omega"), data.get("omega_real"), "ω (°/s)", True


# ──────────────────────────────────────────────────────────────
# Construtores de sinal
#
# Cada construtor recebe (data, log) e devolve um dicionário:
#   {"kind": "xy" | "time", "xlabel", "ylabel", "title",
#    "curves": [{"label", "x", "y", "ls"?, "lw"?, "alpha"?}],
#    "points": [{"label", "x", "y", "marker"?, "size"?}]}
# ou None quando não há dados.
# ──────────────────────────────────────────────────────────────

def _sig_trajectory(data, log):
    curves = [{"label": "trajetória", "x": data["x"], "y": data["y"], "lw": 1.8}]
    points = []
    if _has_finite(data.get("goal_x")):
        points.append({"label": "goals", "x": data["goal_x"], "y": data["goal_y"],
                       "marker": "o", "size": 36})
    if _has_finite(data.get("wp_x")):
        points.append({"label": "waypoints", "x": data["wp_x"], "y": data["wp_y"],
                       "marker": "x", "size": 24})
    if log.planned_path:
        px = np.array([p[0] for p in log.planned_path])
        py = np.array([p[1] for p in log.planned_path])
        curves.append({"label": "planejado", "x": px, "y": py, "ls": "--", "lw": 1.4})
    if log.planned_curve:
        curves.append({"label": "curva planejada",
                       "x": log.planned_curve["x"], "y": log.planned_curve["y"],
                       "ls": "--", "lw": 1.4})
    return {"kind": "xy", "xlabel": "x (m)", "ylabel": "y (m)",
            "title": "Trajetória XY", "curves": curves, "points": points}


def _sig_orientation(data, log):
    t = data["t"]
    curves = [{"label": "θ", "x": t, "y": np.degrees(data["theta"])}]
    if _has_finite(data.get("goal_theta")):
        curves.append({"label": "θ desejado", "x": t,
                       "y": np.degrees(data["goal_theta"]), "ls": "--"})
    return {"kind": "time", "xlabel": "t (s)", "ylabel": "θ (°)",
            "title": "Orientação", "curves": curves}


def _sig_pos_error(data, log):
    rho = _xy_error(data)
    if rho is None:
        return None
    return {"kind": "time", "xlabel": "t (s)", "ylabel": "ρ (m)",
            "title": "Erro de posição (distância ao goal)",
            "curves": [{"label": "ρ", "x": data["t"], "y": rho}]}


def _sig_ori_error(data, log):
    err = _theta_error(data)
    if err is None:
        return None
    return {"kind": "time", "xlabel": "t (s)", "ylabel": "Δθ (°)",
            "title": "Erro de orientação",
            "curves": [{"label": "Δθ", "x": data["t"], "y": np.degrees(err)}]}


def _sig_linear(data, log):
    cmd, real, ylabel = _linear_pair(data, log.robot_type)
    if not _has_finite(cmd) and not _has_finite(real):
        return None
    t = data["t"]
    curves = []
    if _has_finite(cmd):
        curves.append({"label": "cmd", "x": t, "y": cmd, "lw": 1.6})
    if _has_finite(real):
        curves.append({"label": "real", "x": t, "y": real, "ls": "--", "lw": 1.2})
    return {"kind": "time", "xlabel": "t (s)", "ylabel": ylabel,
            "title": "Velocidade linear — cmd vs real", "curves": curves}


def _sig_angular(data, log):
    cmd, real, ylabel, to_deg = _angular_pair(data, log.robot_type)
    if not _has_finite(cmd) and not _has_finite(real):
        return None
    t = data["t"]
    curves = []
    if _has_finite(cmd):
        curves.append({"label": "cmd", "x": t,
                       "y": np.degrees(cmd) if to_deg else cmd, "lw": 1.6})
    if _has_finite(real):
        curves.append({"label": "real", "x": t,
                       "y": np.degrees(real) if to_deg else real,
                       "ls": "--", "lw": 1.2})
    return {"kind": "time", "xlabel": "t (s)", "ylabel": ylabel,
            "title": "Velocidade angular — cmd vs real", "curves": curves}


def _sig_linear_error(data, log):
    cmd, real, ylabel = _linear_pair(data, log.robot_type)
    if not (_has_finite(cmd) and _has_finite(real)):
        return None
    return {"kind": "time", "xlabel": "t (s)", "ylabel": f"Δ {ylabel}",
            "title": "Erro de velocidade linear (cmd − real)",
            "curves": [{"label": "Δ", "x": data["t"], "y": np.asarray(cmd) - np.asarray(real)}]}


def _sig_angular_error(data, log):
    cmd, real, ylabel, to_deg = _angular_pair(data, log.robot_type)
    if not (_has_finite(cmd) and _has_finite(real)):
        return None
    err = np.asarray(cmd) - np.asarray(real)
    return {"kind": "time", "xlabel": "t (s)", "ylabel": f"Δ {ylabel}",
            "title": "Erro de velocidade angular (cmd − real)",
            "curves": [{"label": "Δ", "x": data["t"],
                        "y": np.degrees(err) if to_deg else err}]}


def _sig_wp_index(data, log):
    if "wp_index" not in data:
        return None
    return {"kind": "time", "xlabel": "t (s)", "ylabel": "índice",
            "title": "Waypoint atual",
            "curves": [{"label": "wp_index", "x": data["t"], "y": data["wp_index"]}]}


def _sig_commands(data, log):
    fields = _ROBOT_CMD_FIELDS.get(log.robot_type, [])
    curves = []
    for field in fields:
        if _has_finite(data.get(field)):
            curves.append({"label": field, "x": data["t"], "y": data[field]})
    if not curves:
        return None
    return {"kind": "time", "xlabel": "t (s)", "ylabel": "comando",
            "title": "Comandos de controle", "curves": curves}


SIGNALS = [
    ("trajectory", "Trajetória XY", _sig_trajectory),
    ("orientation", "Orientação θ(t)", _sig_orientation),
    ("pos_error", "Erro de posição ρ(t)", _sig_pos_error),
    ("ori_error", "Erro de orientação Δθ(t)", _sig_ori_error),
    ("linear", "Vel. linear (cmd vs real)", _sig_linear),
    ("angular", "Vel. angular (cmd vs real)", _sig_angular),
    ("linear_error", "Erro vel. linear (cmd−real)", _sig_linear_error),
    ("angular_error", "Erro vel. angular (cmd−real)", _sig_angular_error),
    ("wp_index", "Índice do waypoint", _sig_wp_index),
    ("commands", "Comandos de controle", _sig_commands),
]

SIGNAL_MAP = {sig_id: (sig_id, label, fn) for sig_id, label, fn in SIGNALS}


# ──────────────────────────────────────────────────────────────
# Desenho de um subplot
# ──────────────────────────────────────────────────────────────

def _safe_legend(ax):
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return
    ncol = 1 if len(handles) <= 8 else 2
    ax.legend(handles, labels, fontsize=7, ncol=ncol, loc="best", framealpha=0.7)


def draw_signal(ax, sig_id, robot_indices, logs, robot_colors, overlay):
    """Desenha um sinal (eventualmente sobreposto por robô) no eixo ``ax``."""
    builder = SIGNAL_MAP[sig_id][2]
    specs = []
    for index in robot_indices:
        log = logs.get(index)
        if log is None or not log.frames:
            continue
        spec = builder(log.to_numpy(), log)
        if spec is not None:
            specs.append((index, spec))

    if not specs:
        ax.text(0.5, 0.5, "Sem dados para este sinal",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="gray")
        ax.set_xticks([])
        ax.set_yticks([])
        return

    ref = specs[0][1]
    for index, spec in specs:
        color = robot_colors.get(index, "C0")
        for curve in spec.get("curves", []):
            label = f"B{index}-{curve['label']}" if overlay else curve["label"]
            ax.plot(curve["x"], curve["y"], color=color,
                    linestyle=curve.get("ls", "-"),
                    linewidth=curve.get("lw", 1.5),
                    alpha=curve.get("alpha", 0.9), label=label)
        for point in spec.get("points", []):
            label = f"B{index}-{point['label']}" if overlay else point["label"]
            marker = point.get("marker", "o")
            common = dict(s=point.get("size", 30), marker=marker,
                          linewidths=1.2, label=label)
            if marker in ("o", "s", "^", "D", "v", "<", ">"):
                ax.scatter(point["x"], point["y"], facecolors="none",
                           edgecolors=color, **common)
            else:
                ax.scatter(point["x"], point["y"], color=color, **common)

    title = ref.get("title", SIGNAL_MAP[sig_id][1])
    if not overlay and len(robot_indices) == 1:
        title = f"B-Bot{robot_indices[0]} — {title}"
    ax.set_xlabel(ref.get("xlabel", ""))
    ax.set_ylabel(ref.get("ylabel", ""))
    ax.set_title(title, fontsize=10)
    if ref.get("kind") == "xy":
        ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.4)
    _safe_legend(ax)


# ──────────────────────────────────────────────────────────────
# Janela interativa
# ──────────────────────────────────────────────────────────────

class InteractivePlotWindow:
    """Janela Tkinter com controles e uma figura Matplotlib embutida."""

    def __init__(self, multi_log: MultiRobotLog, title: str = "HiveBr — Plot"):
        import tkinter as tk
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import (
            FigureCanvasTkAgg, NavigationToolbar2Tk,
        )

        try:
            from matplotlib import colormaps
            cmap = colormaps["tab10"]
        except Exception:  # matplotlib < 3.5
            import matplotlib.cm as cm
            cmap = cm.get_cmap("tab10")

        self._tk = tk
        self.multi_log = multi_log
        self.logs = multi_log.logs

        self.robot_indices = sorted(self.logs)
        self.robot_colors = {
            index: cmap(position % 10)
            for position, index in enumerate(self.robot_indices)
        }

        self.figure = Figure(figsize=(9, 6), dpi=100)

        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1280x820")

        self._build_controls()
        self._build_canvas(FigureCanvasTkAgg, NavigationToolbar2Tk)
        self._replot()

    def show(self):
        """Exibe a janela (bloqueia até ser fechada)."""
        self.root.mainloop()

    # ── construção da UI ───────────────────────────────────────

    def _build_controls(self):
        tk = self._tk
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, width=290, padx=10, pady=10)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        right = tk.Frame(main)
        right.pack(side="right", fill="both", expand=True)
        self.right_frame = right

        # Robôs
        tk.Label(left, text="Robôs na arena", font=("TkDefaultFont", 10, "bold"))\
            .pack(anchor="w")
        self.robot_list = tk.Listbox(left, selectmode=tk.EXTENDED,
                                     exportselection=False, height=6)
        for index in self.robot_indices:
            log = self.logs[index]
            self.robot_list.insert("end", f"B-Bot {index}  ({log.robot_type})")
        self.robot_list.pack(fill="x", pady=(0, 8))
        for position in range(len(self.robot_indices)):
            self.robot_list.selection_set(position)

        robot_buttons = tk.Frame(left)
        robot_buttons.pack(fill="x", pady=(0, 10))
        tk.Button(robot_buttons, text="Todos",
                  command=self._select_all_robots).pack(side="left")
        tk.Button(robot_buttons, text="Nenhum",
                  command=self._clear_robots).pack(side="left", padx=6)

        # Sinais
        tk.Label(left, text="Sinais", font=("TkDefaultFont", 10, "bold"))\
            .pack(anchor="w")
        self.signal_vars = {}
        for sig_id, label, _ in SIGNALS:
            var = tk.BooleanVar(value=(sig_id == "trajectory"))
            self.signal_vars[sig_id] = var
            tk.Checkbutton(left, text=label, variable=var,
                           anchor="w", justify="left").pack(fill="x")

        # Grade
        grid = tk.LabelFrame(left, text="Grade de subplots", padx=6, pady=6)
        grid.pack(fill="x", pady=10)
        self.rows_var = tk.IntVar(value=2)
        self.cols_var = tk.IntVar(value=2)
        tk.Label(grid, text="Linhas:").grid(row=0, column=0, sticky="w")
        tk.Spinbox(grid, from_=1, to=6, width=4,
                   textvariable=self.rows_var).grid(row=0, column=1)
        tk.Label(grid, text="Colunas:").grid(row=1, column=0, sticky="w")
        tk.Spinbox(grid, from_=1, to=6, width=4,
                   textvariable=self.cols_var).grid(row=1, column=1)

        # Modo
        self.overlay_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left, text="Sobrepor robôs no mesmo subplot",
                       variable=self.overlay_var, wraplength=250,
                       justify="left", anchor="w").pack(fill="x", pady=(0, 10))

        # Ações
        tk.Button(left, text="Atualizar", command=self._replot)\
            .pack(fill="x", pady=2)
        tk.Button(left, text="Salvar plot", command=self._save_plot)\
            .pack(fill="x", pady=2)
        tk.Button(left, text="Fechar", command=self.root.destroy)\
            .pack(fill="x", pady=2)

        self.status = tk.Label(left, text="", fg="#555", wraplength=260,
                               justify="left")
        self.status.pack(fill="x", pady=(8, 0), side="bottom")

    def _build_canvas(self, FigureCanvasTkAgg, NavigationToolbar2Tk):
        container = self.right_frame
        self.canvas = FigureCanvasTkAgg(self.figure, master=container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, container)
        toolbar.update()

    # ── seleções ───────────────────────────────────────────────

    def _select_all_robots(self):
        self.robot_list.selection_set(0, "end")

    def _clear_robots(self):
        self.robot_list.selection_clear(0, "end")

    def _selected_robots(self):
        return [self.robot_indices[pos]
                for pos in self.robot_list.curselection()]

    def _selected_signals(self):
        return [sig_id for sig_id, _, _ in SIGNALS
                if self.signal_vars[sig_id].get()]

    # ── plot ───────────────────────────────────────────────────

    def _replot(self):
        self.figure.clear()
        robot_indices = self._selected_robots()
        signal_ids = self._selected_signals()

        if not robot_indices or not signal_ids:
            self.figure.text(0.5, 0.5, "Selecione robô(s) e sinal(is)",
                             ha="center", va="center", fontsize=12, color="gray")
            self.canvas.draw_idle()
            self.status.config(text="Nada selecionado.")
            return

        rows = max(1, int(self.rows_var.get()))
        cols = max(1, int(self.cols_var.get()))
        overlay = bool(self.overlay_var.get())

        if overlay:
            items = [(sig_id, robot_indices) for sig_id in signal_ids]
        else:
            items = [(sig_id, [index])
                     for sig_id in signal_ids for index in robot_indices]

        cells = rows * cols
        shown = items[:cells]

        for position in range(cells):
            ax = self.figure.add_subplot(rows, cols, position + 1)
            if position < len(shown):
                sig_id, indices = shown[position]
                draw_signal(ax, sig_id, indices, self.logs,
                            self.robot_colors, overlay)
            else:
                ax.axis("off")

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.status.config(
            text=f"{len(shown)} de {len(items)} gráfico(s) — grade {rows}x{cols}"
        )

    # ── salvar ─────────────────────────────────────────────────

    def _save_plot(self):
        from tkinter import filedialog

        plots_dir = os.path.abspath("./plots")
        os.makedirs(plots_dir, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Salvar plot",
            initialdir=plots_dir,
            initialfile="plot.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
        )
        if not path:
            return
        self.figure.savefig(path, dpi=150, bbox_inches="tight")
        self.status.config(text=f"Salvo: {path}")
        print(f"[PlotWindow] Figura salva em '{path}'")


def show_interactive_plot(multi_log: MultiRobotLog,
                          title: str = "HiveBr — Plot Interativo"):
    """Abre a janela interativa de plot (bloqueante até ser fechada)."""
    if multi_log is None or not multi_log:
        print("[PlotWindow] Nenhum dado para plotar.")
        return
    InteractivePlotWindow(multi_log, title=title).show()
