from __future__ import annotations

import math

import numpy as np
import pygame

from .hexagonal_holonomic import HexagonalHolonomicRobot
from hivebr.engine.geometry import clamp


class HexagonalHolonomicLineFollower(HexagonalHolonomicRobot):
    """Hexagonal holonomic robot (3 omni-wheels) with TCRT5000 analog line sensors.

    Maintains the same kinematics as :class:`HexagonalHolonomicRobot` (commands
    ``{"omega1": ..., "omega2": ..., "omega3": ...}`` or ``{"vx": ..., "vy": ...}``
    or ``{"v": ..., "omega": ...}``), but adds a set of analog line sensors
    mounted on a horizontal bar in front of the body.

    The sensors are sampled from a :class:`LineTrackMap` via
    :meth:`read_line_sensors`, returning analog values in ``[0, 1]``
    (``1`` = black line, ``0`` = light background) and computing the line
    position error relative to the robot center.

    Configuration (``robot`` block):

    ``num_sensors``
        Number of sensors (typically ``2``, ``5`` or ``8``). Default ``5``.
    ``sensor_offset``
        Distance ahead of robot center, in meters.
    ``sensor_span``
        Total width occupied by the sensor array, in meters.
    ``sensor_aperture``
        Radius of area sampled by each sensor, in meters.
    ``sensor_noise``
        Std of analog noise added to readings.
    ``line_threshold``
        Threshold above which sensor counts as "on line".

    Lap timing (same as LineFollowerRobot):
    ``lap_detection_radius``, ``min_lap_distance``, ``min_lap_time``, ``lost_timeout``
    """

    def __init__(self, config: dict):
        super().__init__(config)
        c = config["robot"]

        # Body dimensions (for drawing)
        self.body_length = float(c.get("length", 0.10))
        self.body_width = float(c.get("width", 0.10))
        # radius is already set by parent (distance center to wheel)

        # Line sensor config
        self.num_sensors = int(c.get("num_sensors", 5))
        if self.num_sensors < 1:
            self.num_sensors = 1

        self.sensor_offset = float(
            c.get("sensor_offset", self.body_length * 0.5)
        )
        line_width = float(c.get("line_width", 0.02))
        if "sensor_span" in c:
            self.sensor_span = float(c["sensor_span"])
        else:
            # Sensor spacing slightly smaller than line width so track
            # always crosses adjacent sensors (works for 2, 5 or 8 sensors).
            default_span = min(
                self.body_width * 0.9,
                max(line_width, line_width * 0.75 * (self.num_sensors - 1)),
            )
            self.sensor_span = float(default_span)
        self.sensor_aperture = float(c.get("sensor_aperture", 0.004))
        self.sensor_noise = float(c.get("sensor_noise", 0.0))
        self.line_threshold = float(c.get("line_threshold", 0.5))

        self.sensor_local = self._build_sensor_positions()
        if self.num_sensors > 1:
            self.sensor_weights = np.linspace(-1.0, 1.0, self.num_sensors)
        else:
            self.sensor_weights = np.zeros(1)

        self.sensor_readings = np.zeros(self.num_sensors)
        self.line_error = 0.0
        self.line_position = 0.0
        self.line_lost = True
        self._last_sign = 0.0

        # ---- Lap timing / progress ----
        self.lap_detection_radius = float(c.get("lap_detection_radius", 0.15))
        self.min_lap_distance = float(c.get("min_lap_distance", 1.0))
        self.min_lap_time = float(c.get("min_lap_time", 1.0))
        self.lost_timeout = float(c.get("lost_timeout", 1.0))
        self.reset_laps()

    @property
    def lap_count(self):
        """Number of completed laps."""
        return len(self.lap_times)

    def _build_sensor_positions(self) -> list[np.ndarray]:
        """Local positions of sensors: (x_fwd, y_lateral) relative to body center."""
        if self.num_sensors <= 1:
            offsets = [0.0]
        else:
            offsets = np.linspace(
                -self.sensor_span / 2.0,
                self.sensor_span / 2.0,
                self.num_sensors,
            )
        return [np.array([self.sensor_offset, float(y)]) for y in offsets]

    def reset(self):
        super().reset()
        self.sensor_readings = np.zeros(self.num_sensors)
        self.line_error = 0.0
        self.line_position = 0.0
        self.line_lost = True
        self._last_sign = 0.0
        self.reset_laps()

    def set_initial_pose(self, x, y, theta=0.0):
        super().set_initial_pose(x, y, theta)
        self.reset_laps()

    def state(self):
        state = super().state()
        current_lap = (
            self.finish_time
            if self.finished
            else (self.time - self.lap_start_time)
        )
        state.update(
            {
                "line_follower": True,
                "num_sensors": self.num_sensors,
                "sensors": self.sensor_readings.tolist(),
                "line_error": self.line_error,
                "line_position": self.line_position,
                "line_lost": self.line_lost,
                "time": self.time,
                "finished": self.finished,
                "finish_time": self.finish_time,
                "lap_count": len(self.lap_times),
                "lap_times": list(self.lap_times),
                "last_lap": self.lap_times[-1] if self.lap_times else None,
                "lap_avg": float(np.mean(self.lap_times)) if self.lap_times else None,
                "current_lap": current_lap,
            }
        )
        return state

    def lap_statistics(self) -> dict:
        """Lap summary (count, last, mean, best, worst)."""
        if not self.lap_times:
            return {"count": 0, "last": None, "mean": None, "best": None, "worst": None}
        times = np.asarray(self.lap_times, dtype=float)
        return {
            "count": int(times.size),
            "last": float(times[-1]),
            "mean": float(times.mean()),
            "best": float(times.min()),
            "worst": float(times.max()),
        }

    def sensor_world_position(self, index: int) -> np.ndarray:
        """World position of sensor ``index``."""
        lx, ly = self.sensor_local[index]
        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)
        return np.array(
            [
                self.x + lx * cos_t - ly * sin_t,
                self.y + lx * sin_t + ly * cos_t,
            ]
        )

    def read_line_sensors(self, line_map) -> np.ndarray:
        """Sample sensors and update ``line_error``/``line_lost``.

        Parameters
        ----------
        line_map:
            A :class:`LineTrackMap`. If ``None``, returns zero readings.

        Returns
        -------
        numpy.ndarray
            Analog readings in ``[0, 1]`` (``1`` = black line).
        """
        if line_map is None:
            self.sensor_readings = np.zeros(self.num_sensors)
            self.line_lost = True
            return self.sensor_readings

        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)
        values = np.empty(self.num_sensors)

        for i, (lx, ly) in enumerate(self.sensor_local):
            wx = self.x + lx * cos_t - ly * sin_t
            wy = self.y + lx * sin_t + ly * cos_t
            value = line_map.sample(wx, wy, self.sensor_aperture)
            if self.sensor_noise > 0.0:
                value += float(np.random.normal(0.0, self.sensor_noise))
            values[i] = clamp(value, 0.0, 1.0)

        self.sensor_readings = values

        total = float(values.sum())
        if total > 1e-6:
            self.line_error = float(np.dot(self.sensor_weights, values) / total)
            self.line_lost = False
        else:
            self.line_lost = True
            if abs(self.line_error) < 1e-6:
                self.line_error = self._last_sign

        if abs(self.line_error) > 1e-6:
            self._last_sign = 1.0 if self.line_error > 0.0 else -1.0

        self.line_position = self.line_error * (self.sensor_span / 2.0)
        return values

    # Convenience alias
    read_sensors = read_line_sensors

    def step(self, command: dict, dt: float):
        if self.finished:
            command = {"v": 0.0, "omega": 0.0}
        super().step(command, dt)
        self._update_progress(dt)

    def _update_progress(self, dt: float):
        """Time laps (closed track) and end-of-track (open track)."""
        self.time += dt
        self.distance_traveled += abs(self.v) * dt

        # ---- End of track: line lost for long enough ----
        if not self.finished and self.line_lost:
            self._lost_time += dt
            if (
                self._lost_time >= self.lost_timeout
                and self.distance_traveled >= self.min_lap_distance
            ):
                self.finished = True
                self.finish_time = self.time
                print(
                    f"[HexHolonomicLineFollower] Track end detected at t={self.time:.2f}s "
                    f"(distance={self.distance_traveled:.2f}m)"
                )
                return

        if not self.line_lost:
            self._lost_time = 0.0

        # ---- Lap detection: return to start ----
        if not self.finished and self.lap_times:
            dist_to_start = np.linalg.norm(self.position - self.lap_origin)
            if (
                dist_to_start < self.lap_detection_radius
                and self.distance_traveled > self.min_lap_distance
                and (self.time - self.lap_start_time) > self.min_lap_time
            ):
                lap_time = self.time - self.lap_start_time
                self.lap_times.append(lap_time)
                self.lap_start_time = self.time
                self.lap_origin = self.position.copy()
                print(
                    f"[HexHolonomicLineFollower] Lap {len(self.lap_times)}: "
                    f"{lap_time:.2f}s"
                )

    def reset_laps(self):
        """Reset lap timer and statistics."""
        self.time = 0.0
        self.distance_traveled = 0.0
        self.lap_times: list[float] = []
        self.lap_start_time = 0.0
        self.lap_origin = self.position.copy()
        self._left_start = False
        self.finished = False
        self.finish_time = None
        self._lost_time = 0.0

    def draw(self, screen, camera):
        # Draw everything from parent (hexagon + wheels + axes + path)
        super().draw(screen, camera)

        # Draw line sensor bar on top (green line with sensor dots)
        if self.num_sensors > 0:
            cos_t = math.cos(self.theta)
            sin_t = math.sin(self.theta)

            # Sensor bar endpoints
            bar_left = np.array([
                self.x + self.sensor_offset * cos_t - (self.sensor_span / 2) * sin_t,
                self.y + self.sensor_offset * sin_t + (self.sensor_span / 2) * cos_t
            ])
            bar_right = np.array([
                self.x + self.sensor_offset * cos_t + (self.sensor_span / 2) * sin_t,
                self.y + self.sensor_offset * sin_t - (self.sensor_span / 2) * cos_t
            ])

            bar_left_s = camera.world_to_screen(*bar_left)
            bar_right_s = camera.world_to_screen(*bar_right)

            # Bar color: green if line detected, red if lost
            bar_color = (0, 200, 0) if not self.line_lost else (200, 0, 0)
            pygame.draw.line(screen, bar_color, bar_left_s, bar_right_s, 3)

            # Individual sensor dots
            for i, (lx, ly) in enumerate(self.sensor_local):
                wx = self.x + lx * cos_t - ly * sin_t
                wy = self.y + lx * sin_t + ly * cos_t
                sx, sy = camera.world_to_screen(wx, wy)

                # Dot color based on reading (0=white, 1=black)
                reading = self.sensor_readings[i] if i < len(self.sensor_readings) else 0
                dot_color = (
                    int(255 * (1 - reading)),
                    int(255 * reading),
                    0
                )
                pygame.draw.circle(screen, dot_color, (int(sx), int(sy)), 4)
                pygame.draw.circle(screen, (0, 0, 0), (int(sx), int(sy)), 4, 1)


def create_hexagonal_holonomic_line_follower(config: dict):
    """Factory for HexagonalHolonomicLineFollower."""
    return HexagonalHolonomicLineFollower(config)