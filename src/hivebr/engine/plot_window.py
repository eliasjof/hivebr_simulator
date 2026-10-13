"""
plot_window.py
--------------
Interactive plot window (Tkinter + Matplotlib) to inspect the data recorded
by :class:`~hivebr.engine.data_logger.DataLogger`.

The window allows the user to:

- select one or **several** B-bots in the hive;
- select the signals to display from a list (XY trajectory, position error,
  orientation error, linear/angular velocity command vs actual, control
  commands, ...);
- choose the subplot grid (1x1, 2x1, 2x2, ...);
- overlay several B-bots in the same subplot or split one B-bot per subplot;
- save the current figure (png/pdf/svg).

Two variables can share the same subplot through dual y-axes (one on the left,
one on the right): the commanded and the actual velocities, or the orientation
and its desired value, are drawn together with a dedicated axis each.

The window is opened by :func:`show_interactive_plot`, usually from the
**Plot Log** button of the simulator or from ``DataLogger.plot()``.
"""

from __future__ import annotations

import os

import numpy as np

from .data_logger import _ROBOT_CMD_FIELDS, MultiRobotLog


# ──────────────────────────────────────────────────────────────
# Helpers
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
    """Return (command, actual, ylabel) of the linear velocity."""
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
    """Return (command, actual, ylabel, in_degrees)."""
    if robot_type == "holonomic":
        return data.get("vx"), data.get("vx_real"), "vx (m/s)", False
    if robot_type == "ackermann":
        return data.get("steer"), data.get("steer_real"), r"$\delta$ (deg)", True
    return data.get("omega"), data.get("omega_real"), r"$\omega$ (deg/s)", True


# ──────────────────────────────────────────────────────────────
# Signal builders
#
# Each builder receives (data, log) and returns a dict of panels:
#   {panel_key: {"kind": "xy" | "time", "xlabel", "ylabel", "title",
#                "curves": [{"label", "x", "y", "ls"?, "lw"?, "alpha"?}],
#                "points": [{"label", "x", "y", "marker"?, "size"?}]}}
#
# A curve with "axis": "right" is plotted against a twin right-hand axis,
# so two variables can share the same subplot (left/right y-axes).
# ──────────────────────────────────────────────────────────────

def _sig_trajectory(data, log):
    curves = [{"label": "path", "x": data["x"], "y": data["y"], "lw": 1.8}]
    points = []
    # if _has_finite(data.get("goal_x")):
    #     points.append({"label": "goals", "x": data["goal_x"], "y": data["goal_y"],
    #                    "marker": "o", "size": 36})
    if _has_finite(data.get("wp_x")):
        points.append({"label": "waypoints", "x": data["wp_x"], "y": data["wp_y"],
                       "marker": "x", "size": 12})
    if log.planned_path:
        px = np.array([p[0] for p in log.planned_path])
        py = np.array([p[1] for p in log.planned_path])
        curves.append({"label": "planned", "x": px, "y": py, "ls": "--", "lw": 1.1})
    if log.planned_curve:
        curves.append({"label": "planned curve",
                       "x": log.planned_curve["x"], "y": log.planned_curve["y"],
                       "ls": "--", "lw": 1.1})
    return {
        "xy": {"kind": "xy", "xlabel": "x (m)", "ylabel": "y (m)",
               "title": "Trajectory XY", "curves": curves, "points": points},
    }


def _sig_orientation(data, log):
    t = data["t"]
    curves = [{"label": r"$\theta$", "x": t, "y": np.degrees(data["theta"])}]
    if _has_finite(data.get("goal_theta")):
        curves.append({"label": r"$\theta_{des}$", "x": t,
                       "y": np.degrees(data["goal_theta"]), "ls": "--"})
    return {"orientation": {"kind": "time", "xlabel": "t (s)",
                            "ylabel": r"$\theta$ (deg)",
                            "title": "Orientation", "curves": curves}}


def _sig_pos_error(data, log):
    rho = _xy_error(data)
    if rho is None:
        return None
    return {"rho": {"kind": "time", "xlabel": "t (s)", "ylabel": r"$\rho$ (m)",
                    "title": "Position error (distance to goal)",
                    "curves": [{"label": r"$\rho$", "x": data["t"], "y": rho}]}}


def _sig_ori_error(data, log):
    err = _theta_error(data)
    if err is None:
        return None
    return {"theta_e": {"kind": "time", "xlabel": "t (s)",
                        "ylabel": r"$\theta_e$ (deg)",
                        "title": "Orientation error",
                        "curves": [{"label": r"$\theta_e$", "x": data["t"],
                                    "y": np.degrees(err)}]}}


def _sig_linear(data, log):
    cmd, real, ylabel = _linear_pair(data, log.robot_type)
    if not _has_finite(cmd) and not _has_finite(real):
        return None
    t = data["t"]
    curves = []
    if _has_finite(cmd):
        curves.append({"label": "command", "x": t, "y": cmd, "lw": 1.6})
    if _has_finite(real):
        curves.append({"label": "actual", "x": t, "y": real, "axis": "right",
                       "ls": "--", "lw": 1.2})
    panel = {"kind": "time", "xlabel": "t (s)", "ylabel": ylabel,
             "title": "Linear velocity - command vs actual", "curves": curves}
    if _has_finite(real):
        panel["ylabel_right"] = ylabel
    return {"linear": panel}


def _sig_angular(data, log):
    cmd, real, ylabel, to_deg = _angular_pair(data, log.robot_type)
    if not _has_finite(cmd) and not _has_finite(real):
        return None
    t = data["t"]
    curves = []
    if _has_finite(cmd):
        curves.append({"label": "command", "x": t,
                       "y": np.degrees(cmd) if to_deg else cmd, "lw": 1.6})
    if _has_finite(real):
        curves.append({"label": "actual", "x": t,
                       "y": np.degrees(real) if to_deg else real,
                       "axis": "right", "ls": "--", "lw": 1.2})
    panel = {"kind": "time", "xlabel": "t (s)", "ylabel": ylabel,
             "title": "Angular velocity - command vs actual", "curves": curves}
    if _has_finite(real):
        panel["ylabel_right"] = ylabel
    return {"angular": panel}


def _sig_linear_error(data, log):
    cmd, real, ylabel = _linear_pair(data, log.robot_type)
    if not (_has_finite(cmd) and _has_finite(real)):
        return None
    return {"lin_err": {"kind": "time", "xlabel": "t (s)",
                        "ylabel": f"error ({ylabel})",
                        "title": "Linear velocity error (command - actual)",
                        "curves": [{"label": "error", "x": data["t"],
                                    "y": np.asarray(cmd) - np.asarray(real)}]}}


def _sig_angular_error(data, log):
    cmd, real, ylabel, to_deg = _angular_pair(data, log.robot_type)
    if not (_has_finite(cmd) and _has_finite(real)):
        return None
    err = np.asarray(cmd) - np.asarray(real)
    return {"ang_err": {"kind": "time", "xlabel": "t (s)",
                        "ylabel": f"error ({ylabel})",
                        "title": "Angular velocity error (command - actual)",
                        "curves": [{"label": "error", "x": data["t"],
                                    "y": np.degrees(err) if to_deg else err}]}}


def _sig_commands(data, log):
    fields = [f for f in _ROBOT_CMD_FIELDS.get(log.robot_type, [])
              if _has_finite(data.get(f))]
    if not fields:
        return None
    curves = [{"label": fields[0], "x": data["t"], "y": data[fields[0]]}]
    for field in fields[1:]:
        curves.append({"label": field, "x": data["t"], "y": data[field],
                       "axis": "right"})
    panel = {"kind": "time", "xlabel": "t (s)", "ylabel": fields[0],
             "title": "Control commands", "curves": curves}
    if len(fields) > 1:
        panel["ylabel_right"] = ", ".join(fields[1:])
    return {"commands": panel}


SIGNALS = [
    ("trajectory", "Trajectory XY", _sig_trajectory),
    ("orientation", "Orientation", _sig_orientation),
    ("pos_error", "Position error (distance to goal)", _sig_pos_error),
    ("ori_error", "Orientation error", _sig_ori_error),
    ("linear", "Linear velocity (command vs actual)", _sig_linear),
    ("angular", "Angular velocity (command vs actual)", _sig_angular),
    ("linear_error", "Linear velocity error", _sig_linear_error),
    ("angular_error", "Angular velocity error", _sig_angular_error),
    ("commands", "Control commands", _sig_commands),
]

SIGNAL_MAP = {sig_id: (sig_id, label, fn) for sig_id, label, fn in SIGNALS}


# ──────────────────────────────────────────────────────────────
# Panel drawing
# ──────────────────────────────────────────────────────────────

def _legend(ax, right_ax=None):
    handles, labels = ax.get_legend_handles_labels()
    if right_ax is not None:
        extra_handles, extra_labels = right_ax.get_legend_handles_labels()
        handles += extra_handles
        labels += extra_labels
    if not handles:
        return
    ncol = 1 if len(handles) <= 8 else 2
    ax.legend(handles, labels, fontsize=7, ncol=ncol, loc="best", framealpha=0.7)


def draw_panel(ax, entries, overlay, robot_colors):
    """Draw one panel, optionally overlaying several B-bots.

    ``entries`` is a list of ``(robot_index, panel)``. Curves flagged with
    ``axis="right"`` are drawn against a twin (right-hand) axis, so two
    variables can share the same subplot.
    """
    if not entries:
        ax.text(0.5, 0.5, "No data for this signal",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=10, color="gray")
        ax.set_xticks([])
        ax.set_yticks([])
        return

    ref = entries[0][1]
    right_ax = None
    for index, panel in entries:
        color = robot_colors.get(index, "C0")
        for curve in panel.get("curves", []):
            # label = f"B{index} {curve['label']}" if overlay else curve["label"]
            label = f"B{index}" if overlay else curve["label"]
            if curve.get("axis") == "right":
                if right_ax is None:
                    right_ax = ax.twinx()
                target = right_ax
            else:
                target = ax
            target.plot(curve["x"], curve["y"], color=color,
                        linestyle=curve.get("ls", "-"),
                        linewidth=curve.get("lw", 1.5),
                        alpha=curve.get("alpha", 0.9), label=label)
        for point in panel.get("points", []):
            label = f"B{index} {point['label']}" if overlay else point["label"]
            marker = point.get("marker", "o")
            common = dict(s=point.get("size", 30), marker=marker,
                          linewidths=1.2, label=label)
            if marker in ("o", "s", "^", "D", "v", "<", ">"):
                ax.scatter(point["x"], point["y"], facecolors="none",
                           edgecolors=color, **common)
            else:
                ax.scatter(point["x"], point["y"], color=color, **common)

    title = ref.get("title", "")
    if not overlay and len(entries) == 1:
        # title = f"B-bot{entries[0][0]} - {title}"
        title = f"B-bot{entries[0][0]}"
    ax.set_xlabel(ref.get("xlabel", ""))
    ax.set_ylabel(ref.get("ylabel", ""))
    ax.set_title(title, fontsize=10)
    if ref.get("kind") == "xy":
        ax.set_aspect("equal", adjustable="datalim")
    ax.grid(True, alpha=0.4)
    if right_ax is not None:
        right_ax.set_ylabel(ref.get("ylabel_right", ""))
    _legend(ax, right_ax)


# ──────────────────────────────────────────────────────────────
# Interactive window
# ──────────────────────────────────────────────────────────────

def _robot_panels(builder, log):
    if log is None or not log.frames:
        return {}
    try:
        panels = builder(log.to_numpy(), log)
    except Exception:
        return {}
    return panels or {}


class InteractivePlotWindow:
    """Tkinter window with controls and an embedded Matplotlib figure."""

    def __init__(self, multi_log: MultiRobotLog, title: str = "HiveBr - Plot"):
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
        """Show the window (blocks until it is closed)."""
        self.root.mainloop()

    # ── UI construction ────────────────────────────────────────

    def _build_controls(self):
        tk = self._tk
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, width=300, padx=10, pady=10)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        right = tk.Frame(main)
        right.pack(side="right", fill="both", expand=True)
        self.right_frame = right

        # B-bots
        tk.Label(left, text="B-bots in the hive",
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.robot_list = tk.Listbox(left, selectmode=tk.EXTENDED,
                                     exportselection=False, height=6)
        for index in self.robot_indices:
            log = self.logs[index]
            self.robot_list.insert("end", f"B-bot {index}  ({log.robot_type})")
        self.robot_list.pack(fill="x", pady=(0, 8))
        for position in range(len(self.robot_indices)):
            self.robot_list.selection_set(position)

        robot_buttons = tk.Frame(left)
        robot_buttons.pack(fill="x", pady=(0, 10))
        tk.Button(robot_buttons, text="All",
                  command=self._select_all_robots).pack(side="left")
        tk.Button(robot_buttons, text="None",
                  command=self._clear_robots).pack(side="left", padx=6)

        # Signals
        tk.Label(left, text="Signals",
                 font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
        self.signal_vars = {}
        for sig_id, label, _ in SIGNALS:
            var = tk.BooleanVar(value=(sig_id == "trajectory"))
            self.signal_vars[sig_id] = var
            tk.Checkbutton(left, text=label, variable=var,
                           anchor="w", justify="left").pack(fill="x")

        # Grid
        grid = tk.LabelFrame(left, text="Subplot grid", padx=6, pady=6)
        grid.pack(fill="x", pady=10)
        self.rows_var = tk.IntVar(value=2)
        self.cols_var = tk.IntVar(value=2)
        tk.Label(grid, text="Rows:").grid(row=0, column=0, sticky="w")
        tk.Spinbox(grid, from_=1, to=8, width=4,
                   textvariable=self.rows_var).grid(row=0, column=1)
        tk.Label(grid, text="Columns:").grid(row=1, column=0, sticky="w")
        tk.Spinbox(grid, from_=1, to=8, width=4,
                   textvariable=self.cols_var).grid(row=1, column=1)

        # Mode
        self.overlay_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left, text="Overlay B-bots in the same subplot",
                       variable=self.overlay_var, wraplength=260,
                       justify="left", anchor="w").pack(fill="x", pady=(0, 10))

        # Actions
        tk.Button(left, text="Update", command=self._replot)\
            .pack(fill="x", pady=2)
        tk.Button(left, text="Reset view", command=self._replot)\
            .pack(fill="x", pady=2)
        tk.Button(left, text="Save plot", command=self._save_plot)\
            .pack(fill="x", pady=2)
        tk.Button(left, text="Close", command=self.root.destroy)\
            .pack(fill="x", pady=2)

        self.status = tk.Label(left, text="", fg="#555", wraplength=270,
                               justify="left")
        self.status.pack(fill="x", pady=(8, 0), side="bottom")

    def _build_canvas(self, FigureCanvasTkAgg, NavigationToolbar2Tk):
        container = self.right_frame
        self.canvas = FigureCanvasTkAgg(self.figure, master=container)
        # The toolbar packs itself at the top: create it before packing the
        # canvas so both stay visible.
        self.toolbar = NavigationToolbar2Tk(self.canvas, container)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        # Mouse-wheel zoom on the subplot under the cursor.
        self.canvas.mpl_connect("scroll_event", self._on_scroll)

    # ── zoom ───────────────────────────────────────────────────

    def _on_scroll(self, event):
        ax = event.inaxes
        if ax is None or event.xdata is None or event.ydata is None:
            return
        factor = 0.8 if event.step > 0 else 1.25
        self._zoom_axes(ax, event.xdata, event.ydata, factor)
        self.canvas.draw_idle()

    @staticmethod
    def _zoom_axes(ax, cx, cy, factor):
        try:
            x_siblings = list(ax.get_shared_x_axes().get_siblings(ax))
            y_siblings = list(ax.get_shared_y_axes().get_siblings(ax))
        except Exception:
            x_siblings, y_siblings = [ax], [ax]
        for sibling in x_siblings:
            x0, x1 = sibling.get_xlim()
            sibling.set_xlim(cx + (x0 - cx) * factor, cx + (x1 - cx) * factor)
        for sibling in y_siblings:
            y0, y1 = sibling.get_ylim()
            sibling.set_ylim(cy + (y0 - cy) * factor, cy + (y1 - cy) * factor)

    # ── selections ─────────────────────────────────────────────

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

    # ── plotting ───────────────────────────────────────────────

    def _build_items(self, signal_ids, robot_indices, overlay):
        cache = {}
        for sig_id in signal_ids:
            builder = SIGNAL_MAP[sig_id][2]
            for index in robot_indices:
                cache[(sig_id, index)] = _robot_panels(builder, self.logs.get(index))

        items = []
        if overlay:
            for sig_id in signal_ids:
                keys = []
                for index in robot_indices:
                    for key in cache[(sig_id, index)]:
                        if key not in keys:
                            keys.append(key)
                for key in keys:
                    entries = [(index, cache[(sig_id, index)][key])
                               for index in robot_indices
                               if key in cache[(sig_id, index)]]
                    items.append(entries)
        else:
            for sig_id in signal_ids:
                for index in robot_indices:
                    for key, panel in cache[(sig_id, index)].items():
                        items.append([(index, panel)])
        return items

    def _replot(self):
        self.figure.clear()
        robot_indices = self._selected_robots()
        signal_ids = self._selected_signals()

        if not robot_indices or not signal_ids:
            self.figure.text(0.5, 0.5, "Select B-bot(s) and signal(s)",
                             ha="center", va="center", fontsize=12, color="gray")
            self.canvas.draw_idle()
            self.status.config(text="Nothing selected.")
            return

        rows = max(1, int(self.rows_var.get()))
        cols = max(1, int(self.cols_var.get()))
        overlay = bool(self.overlay_var.get())

        items = self._build_items(signal_ids, robot_indices, overlay)
        cells = rows * cols
        shown = items[:cells]

        for position in range(cells):
            ax = self.figure.add_subplot(rows, cols, position + 1)
            if position < len(shown):
                draw_panel(ax, shown[position], overlay, self.robot_colors)
            else:
                ax.axis("off")

        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.status.config(
            text=f"{len(shown)} of {len(items)} plot(s) shown - grid {rows}x{cols}"
        )

    # ── saving ─────────────────────────────────────────────────

    def _save_plot(self):
        from tkinter import filedialog

        plots_dir = os.path.abspath("./plots")
        os.makedirs(plots_dir, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save plot",
            initialdir=plots_dir,
            initialfile="plot.png",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
        )
        if not path:
            return
        self.figure.savefig(path, dpi=150, bbox_inches="tight")
        self.status.config(text=f"Saved: {path}")
        print(f"[PlotWindow] Figure saved to '{path}'")


def show_interactive_plot(multi_log: MultiRobotLog,
                          title: str = "HiveBr - Interactive Plot"):
    """Open the interactive plot window (blocks until it is closed)."""
    if multi_log is None or not multi_log:
        print("[PlotWindow] No data to plot.")
        return
    InteractivePlotWindow(multi_log, title=title).show()
