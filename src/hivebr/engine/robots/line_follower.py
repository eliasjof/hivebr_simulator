from __future__ import annotations

import math

import numpy as np
import pygame

from .differential import DifferentialRobot
from hivebr.engine.geometry import clamp


class LineFollowerRobot(DifferentialRobot):
    """Robô diferencial com um arranjo de sensores analógicos de linha.

    Mantém a mesma cinemática do :class:`DifferentialRobot` (comandos
    ``{"v": ..., "omega": ...}``), mas adiciona um conjunto de sensores
    TCRT5000 montados numa barra horizontal na frente do corpo. O corpo é um
    quadrado de ``length`` x ``width`` (padrão ``10cm x 10cm``).

    Os sensores são amostrados a partir de um :class:`LineTrackMap` através de
    :meth:`read_line_sensors`, que retorna valores analógicos em ``[0, 1]``
    (``1`` = linha preta, ``0`` = fundo claro) e calcula o erro de posição da
    linha em relação ao centro do robô.

    Configuração (bloco ``robot``):

    ``num_sensors``
        Número de sensores (tipicamente ``2``, ``5`` ou ``8``). Padrão ``5``.
    ``sensor_offset``
        Distância à frente do centro do robô, em metros.
    ``sensor_span``
        Largura total ocupada pelo arranjo, em metros.
    ``sensor_aperture``
        Raio da área amostrada por cada sensor, em metros.
    ``sensor_noise``
        Desvio-padrão do ruído analógico adicionado à leitura.
    ``line_threshold``
        Limiar acima do qual o sensor é considerado "sobre a linha".
    """

    def __init__(self, config: dict):
        super().__init__(config)
        c = config["robot"]

        self.body_length = float(c.get("length", 0.10))
        self.body_width = float(c.get("width", 0.10))
        self.radius = float(c.get("radius", 0.05))

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
            # Espaçamento entre sensores ligeiramente menor que a largura da
            # linha para que a pista sempre cruze sensores adjacentes
            # (funciona para 2, 5 ou 8 sensores).
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

        # ---- cronometragem de voltas / percurso ----
        self.lap_detection_radius = float(c.get("lap_detection_radius", 0.15))
        self.min_lap_distance = float(c.get("min_lap_distance", 1.0))
        self.min_lap_time = float(c.get("min_lap_time", 1.0))
        self.lost_timeout = float(c.get("lost_timeout", 1.0))
        self.reset_laps()

    def reset_laps(self):
        """Zera o cronômetro e as estatísticas de voltas/percurso."""
        self.time = 0.0
        self.distance_traveled = 0.0
        self.lap_times: list[float] = []
        self.lap_start_time = 0.0
        self.lap_origin = self.position.copy()
        self._left_start = False
        self.finished = False
        self.finish_time = None
        self._lost_time = 0.0

    def _build_sensor_positions(self) -> list[np.ndarray]:
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
        """Resumo das voltas (contagem, última, média, melhor, pior)."""
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
        """Posição no mundo do sensor ``index``."""
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
        """Amostra os sensores e atualiza ``line_error``/``line_lost``.

        Parameters
        ----------
        line_map:
            Um :class:`LineTrackMap`. Se ``None``, devolve leituras nulas.

        Returns
        -------
        numpy.ndarray
            Leituras analógicas em ``[0, 1]`` (``1`` = linha preta).
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

    # aliases convenientes
    read_sensors = read_line_sensors

    def step(self, command: dict, dt: float):
        if self.finished:
            command = {"v": 0.0, "omega": 0.0}
        super().step(command, dt)
        self._update_progress(dt)

    def _update_progress(self, dt: float):
        """Cronometra voltas (pista fechada) e fim de percurso (pista aberta)."""
        self.time += dt
        self.distance_traveled += abs(self.v) * dt

        # ---- fim de pista: linha perdida por tempo suficiente ----
        if not self.finished and self.line_lost:
            self._lost_time += dt
            if (
                self._lost_time >= self.lost_timeout
                and self.distance_traveled >= self.min_lap_distance
            ):
                self.finished = True
                self.finish_time = self.time
                print(
                    f"[LineFollower] Fim da pista em {self.finish_time:.2f} s "
                    f"({self.distance_traveled:.2f} m percorridos)."
                )
        elif not self.line_lost:
            self._lost_time = 0.0

        if self.finished:
            return

        # ---- volta completa: retorno ao ponto inicial (com histerese) ----
        distance_to_origin = float(np.linalg.norm(self.position - self.lap_origin))
        exit_radius = 2.5 * self.lap_detection_radius
        if distance_to_origin > exit_radius:
            self._left_start = True

        if (
            self._left_start
            and distance_to_origin <= self.lap_detection_radius
            and (self.time - self.lap_start_time) >= self.min_lap_time
        ):
            lap = self.time - self.lap_start_time
            self.lap_times.append(lap)
            self.lap_start_time = self.time
            self._left_start = False
            stats = self.lap_statistics()
            print(
                f"[LineFollower] Volta {stats['count']} concluída em {lap:.2f} s "
                f"(média {stats['mean']:.2f} s, melhor {stats['best']:.2f} s)."
            )

    @staticmethod
    def _sensor_color(value: float):
        value = clamp(value, 0.0, 1.0)
        base = np.array([70.0, 70.0, 70.0])
        line = np.array([255.0, 50.0, 50.0])
        return tuple((base + (line - base) * value).astype(int))

    def draw(self, screen, camera):
        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)
        rot = np.array([[cos_t, -sin_t], [sin_t, cos_t]])

        half_l = self.body_length / 2.0
        half_w = self.body_width / 2.0
        corners = [
            (-half_l, -half_w),
            (half_l, -half_w),
            (half_l, half_w),
            (-half_l, half_w),
        ]
        body_pts = [
            camera.world_to_screen(*(rot @ np.array(c) + self.position))
            for c in corners
        ]
        pygame.draw.polygon(screen, tuple(self.colors["robot"]), body_pts)
        pygame.draw.polygon(screen, (20, 20, 20), body_pts, 2)

        front = self.position + np.array([cos_t, sin_t]) * half_l
        pygame.draw.line(
            screen,
            tuple(self.colors.get("silver", [192, 192, 186])),
            camera.world_to_screen(self.x, self.y),
            camera.world_to_screen(*front),
            2,
        )

        sensor_radius = max(2, int(0.006 * camera.scale))
        for (lx, ly), value in zip(self.sensor_local, self.sensor_readings):
            pos = rot @ np.array([lx, ly]) + self.position
            screen_pos = camera.world_to_screen(*pos)
            pygame.draw.circle(
                screen, self._sensor_color(float(value)), screen_pos, sensor_radius
            )
            pygame.draw.circle(screen, (0, 0, 0), screen_pos, sensor_radius, 1)
