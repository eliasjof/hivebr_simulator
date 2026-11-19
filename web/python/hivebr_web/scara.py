"""Didactic SCARA cell for the browser.

The mobile engine is top-down, so a manipulator gets its own small simulator:
a conveyor, coloured parts, three baskets and a 3-DOF SCARA arm. The UI draws
the cell with an isometric projection, which gives a real third dimension on
the 2D canvas without a WebGL renderer.

Student code drives the cell through this class:

    sim = ScaraSimulator()
    while sim.running:
        sim.step()
        ...
        sim.move_joints(q1, q2, d3)
        sim.pick()
        sim.place()

The kinematics (DH table, homogeneous matrices, forward and inverse) live in
the template, not here: the simulator only applies the joint values it
receives.  The tool point is the lower face of the electromagnet, so a target
``z`` is the top of a part and the prismatic joint has to descend to reach it.
"""
from __future__ import annotations

import csv
import json
import math
import os
import uuid

from . import host, urdf

# Fixed palette shared with the renderer. The ids are stable so the student
# code can compare colours without parsing labels.
COLORS = {
    "red": (220, 64, 56),
    "green": (58, 176, 92),
    "blue": (58, 118, 216),
}
COLOR_ORDER = ("red", "green", "blue")

# Geometry in metres. These values match the reference URDF; the simulator
# itself reads the live model, so a student who edits scara_cell.urdf gets a
# robot with exactly the dimensions written in that file.
L1 = 1.6
L2 = 1.4
BASE_Z = 1.10
BELT_Z = 0.55
PART_HEIGHT = 0.15
BELT_Y = 0.0
BELT_X0 = 2.10
BELT_X1 = 5.90
BASKET_Z = 0.28

# The magnet is the tool point: its lower face touches the top of a part. The
# shoulder is deliberately higher than the belt, so the prismatic joint has to
# lower the electromagnet before a pick. TRANSIT_Z is the safe travel height
# used by the activity loop.
TRANSIT_Z = BELT_Z + PART_HEIGHT + 0.30
PICK_RADIUS = 0.30
PICK_HEIGHT = 0.06
PLACE_RADIUS = 0.42
PLACE_HEIGHT = 0.06

# Home pose: elbow bent, arm over the start of the conveyor and magnet raised.
HOME_Q1 = -0.35
HOME_Q2 = 0.95

BASKETS = (
    {"id": "red", "color": "red", "x": 0.55, "y": 2.10},
    {"id": "green", "color": "green", "x": 1.85, "y": 1.85},
    {"id": "blue", "color": "blue", "x": 2.20, "y": -1.15},
)


def f4(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return round(value, 4) if math.isfinite(value) else None


def _approach(current, target, max_step):
    if abs(target - current) <= max_step:
        return target
    return current + math.copysign(max_step, target - current)


def _approach_angle(current, target, max_step):
    """Approaches an angle through the shortest path (no 2*pi detour)."""
    delta = (target - current + math.pi) % (2.0 * math.pi) - math.pi
    if abs(delta) <= max_step:
        return target
    return current + math.copysign(max_step, delta)


class _NoFrames:
    """Minimal stand-in for the frame builder used by UI refresh commands."""

    def force_full(self):
        pass


class ScaraSimulator:
    """Headless SCARA cell: conveyor, colour sensor, arm and baskets."""

    kind = "scara"
    dt = 1.0 / 30.0
    spawn_interval = 1.8
    belt_speed = 0.55
    joint_step = 0.14
    linear_step = 0.09

    def __init__(self, model_path=None, controller=None):
        from . import simulator as simulator_module

        self.config = {"window": {"title": "scara.title"}}
        self.instance = uuid.uuid4().hex
        self.running = True
        self.running_simulation = True
        self.speed = 1.0
        self.sim_time = 0.0
        self.step_count = 0

        # The URDF is the single source of truth for the arm geometry. A
        # student edits scara_cell.urdf in the editor; the worker writes it to
        # user_scripts, which load_model() checks before the packaged model.
        self.model = urdf.load_model(model_path)
        lengths = self.model["lengths"]
        self.l1 = float(lengths["l1"])
        self.l2 = float(lengths["l2"])
        self.base_z = float(lengths["base_z"])
        self.reach = self.l1 + self.l2
        self.motion_names = [j.get("motion") for j in self.model["chain"] if j.get("motion")]
        self.motion_types = {j.get("motion"): j["type"] for j in self.model["chain"] if j.get("motion")}
        self.joint_limits = {j.get("motion"): j.get("limit", {}) for j in self.model["chain"] if j.get("motion")}
        # The arm starts in a natural ready pose instead of fully stretched:
        # q1 points toward the conveyor, q2 bends the elbow and d3 keeps the
        # magnet at TRANSIT_Z, above the parts on the belt.
        self.home = {name: 0.0 for name in self.motion_names}
        self.home["q1"] = self._limited("q1", HOME_Q1)
        self.home["q2"] = self._limited("q2", HOME_Q2)
        self.home["d3"] = self._limited("d3", TRANSIT_Z - self.base_z)
        self.arm = dict(self.home)
        for key in ("q1", "q2", "d3"):
            self.arm.setdefault(key, 0.0)
        self.target = dict(self.arm)
        self.conveyor = {"on": True, "speed": self.belt_speed}
        self.objects = []
        self.held = None
        self.baskets = [dict(basket, count=0) for basket in BASKETS]
        self.placed = 0
        self.rejected = 0
        self.event = "scara.event.waiting"
        self._spawn_in = 0.6
        self._spawned = 0
        self._next_id = 1
        self._scene_sent = False
        self._theme = "dark"
        self.frames = _NoFrames()
        # The idle editor adopts the simulator created by the script, so the
        # cell stays on screen after the student presses Stop.
        simulator_module.adopt(self)

    # ------------------------------------------------------------ output ----
    def _scene(self):
        return {
            "version": 1,
            "kind": "scara",
            "instance": self.instance,
            "title": "scara.title",
            "theme": self._theme,
            "world": {"width": 8.0, "height": 6.0},
            "scara": {
                "l1": f4(self.l1),
                "l2": f4(self.l2),
                "base_z": f4(self.base_z),
                "reach": f4(self.reach),
                "part_height": f4(PART_HEIGHT),
                "belt": {
                    "x0": BELT_X0, "x1": BELT_X1, "y": BELT_Y,
                    "z": BELT_Z, "width": 0.62,
                },
                "baskets": [dict(basket) for basket in BASKETS],
                "colors": {name: list(rgb) for name, rgb in COLORS.items()},
                # The canvas builds the arm from this URDF payload instead of
                # hard-coded segment lengths. Editing the URDF changes both the
                # physics and the drawing.
                "model": {
                    "name": self.model.get("name"),
                    "source": os.path.basename(self.model.get("source", "")),
                    "base": self.model.get("base"),
                    "tool": self.model.get("tool"),
                    "links": self.model.get("links", {}),
                    "joints": self.model.get("joints", []),
                    "chain": self.model.get("chain", []),
                    "lengths": self.model.get("lengths", {}),
                },
            },
        }

    def _frame(self):
        tip = self.tip()
        return {
            "t": f4(self.sim_time),
            "running": bool(self.running and self.running_simulation),
            "speed": f4(self.speed),
            "kind": "scara",
            "robots": [],
            "scara": {
                "arm": {k: f4(v) for k, v in self.arm.items()},
                "target": {k: f4(v) for k, v in self.target.items()},
                "tip": {"x": f4(tip[0]), "y": f4(tip[1]), "z": f4(tip[2])},
                "reach": f4(self.reach),
                "model_source": os.path.basename(self.model.get("source", "")),
                "conveyor": {"on": bool(self.conveyor["on"]), "speed": f4(self.conveyor["speed"])},
                "objects": [self._object_payload(obj) for obj in self.objects],
                "held": self._object_payload(self.held) if self.held else None,
                "baskets": [dict(basket) for basket in self.baskets],
                "placed": self.placed,
                "rejected": self.rejected,
                "event": self.event,
            },
        }

    @staticmethod
    def _object_payload(obj):
        return {
            "id": obj["id"],
            "color": obj["color"],
            "x": f4(obj["x"]),
            "y": f4(obj["y"]),
            "z": f4(obj["z"]),
        }

    def _emit(self, scene=False):
        if scene or not self._scene_sent:
            host.post("scene", self._scene())
            self._scene_sent = True
        host.post("frame", self._frame())

    def _post_scene(self):
        """Sends the static scene again (refresh command / idle editor)."""
        self._emit(scene=True)

    def mark_dirty(self):
        self._emit()

    # ------------------------------------------------------------- input ----
    def _poll(self):
        h = host.get_host()
        for _ in range(64):
            raw = h.poll()
            if raw is None:
                break
            try:
                msg = json.loads(raw) if isinstance(raw, (str, bytes)) else dict(raw)
            except Exception:
                continue
            cmd = msg.get("cmd")
            if cmd == "stop":
                self.running = False
            elif cmd == "start":
                self.running_simulation = True
            elif cmd == "pause":
                self.running_simulation = False
            elif cmd == "toggle":
                self.running_simulation = not self.running_simulation
            elif cmd == "set_speed":
                try:
                    self.speed = max(0.0, min(8.0, float(msg.get("value", self.speed))))
                except (TypeError, ValueError):
                    pass
            elif cmd == "refresh":
                self._emit(scene=True)
            elif cmd == "reset":
                self.reset()
                self._emit(scene=True)

    # -------------------------------------------------------------- loop ----
    def run(self):
        self._emit(scene=True)
        while self.running:
            self.step()
        self._emit()

    def step(self):
        self._poll()
        if self.running and self.running_simulation:
            self._advance(self.dt)
            self.sim_time += self.dt
            self.step_count += 1
            self._emit()
            host.get_host().sleep(1000.0 * self.dt / max(0.1, self.speed))
        else:
            self._emit()
            host.get_host().sleep(1000.0 * self.dt)
        return self.dt

    def physics_step(self):
        self._advance(self.dt)
        self._emit()

    def reset(self):
        self.arm = dict(self.home)
        self.target = dict(self.home)
        for key in ("q1", "q2", "d3"):
            self.arm.setdefault(key, 0.0)
            self.target.setdefault(key, 0.0)
        self.objects = []
        self.held = None
        self.baskets = [dict(basket, count=0) for basket in BASKETS]
        self.placed = 0
        self.rejected = 0
        self.sim_time = 0.0
        self.step_count = 0
        self._spawn_in = 0.6
        self._spawned = 0
        self._next_id = 1
        self.event = "scara.event.waiting"

    def destroy(self):
        self.running = False

    # ----------------------------------------------------------- conveyor ----
    def set_conveyor(self, speed=None, on=None):
        if on is not None:
            self.conveyor["on"] = bool(on)
        if speed is not None:
            self.conveyor["speed"] = max(0.0, min(2.0, float(speed)))
            self.conveyor["on"] = self.conveyor["speed"] > 0.0

    def conveyor_on(self, speed=None):
        self.set_conveyor(speed=speed if speed is not None else self.belt_speed, on=True)

    def conveyor_off(self):
        self.set_conveyor(on=False)

    # --------------------------------------------------------------- arm ----
    def _limited(self, name, value):
        value = float(value)
        kind = self.motion_types.get(name)
        limit = self.joint_limits.get(name) or {}
        if kind in ("revolute", "continuous"):
            value = (value + math.pi) % (2.0 * math.pi) - math.pi
            if "lower" in limit:
                value = max(float(limit["lower"]), value)
            if "upper" in limit:
                value = min(float(limit["upper"]), value)
        elif kind == "prismatic":
            if "lower" in limit:
                value = max(float(limit["lower"]), value)
            if "upper" in limit:
                value = min(float(limit["upper"]), value)
        return value

    def move_joints(self, q1, q2, d3=0.0):
        """Sets the joint targets; the arm approaches them smoothly."""
        target = dict(self.target)
        target["q1"] = self._limited("q1", q1)
        target["q2"] = self._limited("q2", q2)
        target["d3"] = self._limited("d3", d3)
        self.target = target

    def tip(self):
        x, y, z = urdf.tip(self.model, self.arm)
        return x, y, z

    def elbow(self):
        positions = urdf.joint_positions(self.model, self.arm)
        chain = self.model.get("chain", [])
        if len(chain) > 1:
            return tuple(positions.get(chain[1]["name"], (0.0, 0.0, self.base_z)))
        return 0.0, 0.0, self.base_z

    def model_info(self):
        """Summary used by the URDF activity and by the HUD."""
        return urdf.model_summary(self.model)

    # -------------------------------------------------------------- parts ----
    def detect(self, radius=None):
        """Colour readings of the parts inside the sensor radius."""
        if radius is None:
            radius = max(0.5, self.reach + 0.2)
        out = []
        for obj in self.objects:
            distance = math.hypot(obj["x"], obj["y"])
            if distance <= radius:
                out.append({
                    "id": obj["id"], "color": obj["color"],
                    "x": f4(obj["x"]), "y": f4(obj["y"]), "z": f4(obj["z"]),
                    "distance": f4(distance),
                })
        return out

    def colors(self):
        return sorted({obj["color"] for obj in self.detect()})

    def next_object(self, max_distance=None):
        """Closest reachable part, or None when the belt has nothing to pick."""
        if max_distance is None:
            max_distance = max(0.0, self.reach * 0.92)
        best = None
        for obj in self.objects:
            if math.hypot(obj["x"], obj["y"]) > max_distance:
                continue
            if best is None or obj["x"] < best["x"]:
                best = obj
        return dict(best) if best else None

    def can_pick(self):
        if self.held is not None:
            return False
        x, y, z = self.tip()
        for obj in self.objects:
            if math.hypot(obj["x"] - x, obj["y"] - y) <= PICK_RADIUS and abs(obj["z"] - z) <= PICK_HEIGHT:
                return True
        return False

    def pick(self):
        if not self.can_pick():
            return False
        x, y, z = self.tip()
        best = None
        for obj in self.objects:
            distance = math.hypot(obj["x"] - x, obj["y"] - y)
            if distance <= PICK_RADIUS and abs(obj["z"] - z) <= PICK_HEIGHT:
                if best is None or distance < best[0]:
                    best = (distance, obj)
        if best is None:
            return False
        self.held = best[1]
        # The part hangs from the magnet: its top is the tool point. Snapping
        # here removes the few centimetres the arm still had to travel.
        self.held["x"], self.held["y"], self.held["z"] = x, y, z
        self.objects.remove(best[1])
        self.event = f"scara.event.holding:{self.held['color']}"
        # Emit immediately so the HUD and the canvas show the new state even
        # when the student's loop ends right after the pick.
        self._emit()
        return True

    def basket_for(self, color):
        for basket in self.baskets:
            if basket["color"] == color:
                return dict(basket)
        return None

    def can_place(self):
        if self.held is None:
            return False
        x, y, z = self.tip()
        basket = self.basket_for(self.held["color"])
        if basket is None:
            return False
        return math.hypot(basket["x"] - x, basket["y"] - y) <= PLACE_RADIUS and abs(BASKET_Z - z) <= PLACE_HEIGHT

    def place(self):
        if not self.can_place():
            return False
        basket = self.basket_for(self.held["color"])
        basket["count"] += 1
        for item in self.baskets:
            if item["id"] == basket["id"]:
                item["count"] = basket["count"]
        self.placed += 1
        self.event = f"scara.event.placed:{self.held['color']}"
        self.held = None
        # The last place often ends the student's loop; emit a final frame so
        # the HUD counter matches the printed SCARA OK line.
        self._emit()
        return True

    # ------------------------------------------------------------- export ----
    def export(self, path="scara_relatorio.csv"):
        """Writes the cell report; returns the absolute path."""
        target = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
        with open(target, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["color", "placed", "lost"])
            for basket in self.baskets:
                writer.writerow([basket["color"], basket["count"], self.rejected])
            writer.writerow(["total", self.placed, self.rejected])
            writer.writerow(["time", f4(self.sim_time), ""])
        return target

    # ------------------------------------------------------------ internal ----
    def _advance(self, dt):
        for name, value in list(self.arm.items()):
            target = self.target.get(name, value)
            kind = self.motion_types.get(name)
            if kind in ("revolute", "continuous"):
                self.arm[name] = _approach_angle(value, target, self.joint_step)
            else:
                self.arm[name] = _approach(value, target, self.linear_step)

        if self.held is not None:
            x, y, z = self.tip()
            # The reported z is the top of the part, exactly where the magnet
            # face touches it; the renderer draws the body below that point.
            self.held["x"], self.held["y"], self.held["z"] = x, y, z

        if self.conveyor["on"] and self.conveyor["speed"] > 0.0:
            step = self.conveyor["speed"] * dt
            for obj in list(self.objects):
                obj["x"] -= step
                if obj["x"] < BELT_X0 - 0.15:
                    self.objects.remove(obj)
                    self.rejected += 1
                    self.event = f"scara.event.lost:{obj['color']}"

        self._spawn_in -= dt
        if self._spawn_in <= 0.0:
            self._spawn_in = self.spawn_interval
            self._spawn()

    def _spawn(self):
        color = COLOR_ORDER[self._spawned % len(COLOR_ORDER)]
        self._spawned += 1
        self.objects.append({
            "id": self._next_id,
            "color": color,
            "x": BELT_X1,
            "y": BELT_Y,
            "z": BELT_Z + PART_HEIGHT,
        })
        self._next_id += 1
