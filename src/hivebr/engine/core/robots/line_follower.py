from __future__ import annotations

import math

import numpy as np

from .differential import DifferentialRobot
from hivebr.engine.geometry import clamp


# ---------------------------------------------------------------------------
# Set position on the track (x, y, theta) aligned with the tangent
# ---------------------------------------------------------------------------
def pose_on_track(points: np.ndarray, index: int = 0, lookahead: int = 12):
    """Retorna ``(x, y, theta)`` sobre a pista, alinhado à tangente."""
    n = len(points)
    p0 = points[index % n]
    p1 = points[(index + lookahead) % n]
    theta = np.arctan2(p1[1] - p0[1], p1[0] - p0[0])
    return float(p0[0]), float(p0[1]), float(theta)


# ---------------------------------------------------------------------------
# Random track generator
# ---------------------------------------------------------------------------
def generate_random_track(
    path,
    width_m: float = 4.0,
    height_m: float = 3.0,
    resolution: float = 0.005,
    line_width_m: float = 0.02,
    seed: int = 7,
):
    """Cria uma pista fechada aleatória e a desenha como linha preta."""
    # Note: This uses PIL for image generation, which works in Pyodide
    from PIL import Image, ImageDraw
    from pathlib import Path
    
    rng = np.random.default_rng(seed)
    width_px = int(round(width_m / resolution))
    height_px = int(round(height_m / resolution))

    t = np.linspace(0.0, 2.0 * np.pi, 2000, endpoint=False)
    radius = np.ones_like(t)
    for k in (2, 3, 4):
        amplitude = rng.uniform(0.03, 0.18) / k
        phase = rng.uniform(0.0, 2.0 * np.pi)
        radius += amplitude * np.cos(k * t + phase)
    radius = np.clip(radius, 0.75, 1.05)

    cx, cy = width_m / 2.0, height_m / 2.0
    rx, ry = width_m * 0.36, height_m * 0.36
    xs = cx + rx * radius * np.cos(t)
    ys = cy + ry * radius * np.sin(t)

    image = Image.new("RGB", (width_px, height_px), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    line_px = max(1, int(round(line_width_m / resolution)))
    points_px = [
        (x / resolution, (height_px - 1) - y / resolution)
        for x, y in zip(xs, ys)
    ]
    draw.line(points_px + [points_px[0]], fill=(0, 0, 0), width=line_px, joint="curve")

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)

    return np.column_stack([xs, ys])


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

    def _tcrt5000_response(self, darkness: float) -> float:
        """
        Modela a resposta realística do TCR5000 (circuito pull-up).

        O TCR5000 com resistor de pull-up tem resposta não-linear:
        - Fototransistor: corrente de coletor ~ irradiancia (linear em luz)
        - Com pull-up: Vout = Vcc - Ic*Rpullup → relação inversa
        - Resposta real é logarítmica/gama (~0.5-0.7)
        - Sensor real não vai rail-to-rail: típico 5-95% do range ADC
        - Filtro de luz diurna imperfeito: luz ambiente eleva o piso (~5-15%)

        Parameters
        ----------
        darkness: float
            Escuridão do mapa de linha (0=branco, 1=preto).

        Returns
        -------
        float
            Tensão normalizada [0, 1] onde 1=linha preta, 0=branco.
        """
        # Parâmetros realísticos do TCR5000
        ambient_floor = 0.08   # Piso por luz ambiente (5-15% típico)
        gamma = 0.65           # Curva gama do fototransistor + pull-up
        rail_min = 0.03        # Não chega a 0V (saturation)
        rail_max = 0.97        # Não chega a Vcc (cutoff)

        # Sinal com piso de luz ambiente
        signal = darkness * (1.0 - ambient_floor) + ambient_floor

        # Aplica curva gama (resposta não-linear)
        response = signal ** gamma

        # Clampa para range realístico (não rail-to-rail)
        return rail_min + (rail_max - rail_min) * response

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
        raw_values = np.empty(self.num_sensors)

        # Amostra cada sensor no mapa de linha
        for i, (lx, ly) in enumerate(self.sensor_local):
            wx = self.x + lx * cos_t - ly * sin_t
            wy = self.y + lx * sin_t + ly * cos_t
            darkness = line_map.sample(wx, wy, self.sensor_aperture)
            # Aplica modelo realístico do TCR5000
            value = self._tcrt5000_response(darkness)
            if self.sensor_noise > 0.0:
                value += float(np.random.normal(0.0, self.sensor_noise))
            raw_values[i] = clamp(value, 0.0, 1.0)

        # Cross-talk entre sensores adjacentes (~5% bleed de IR)
        values = raw_values.copy()
        if self.num_sensors > 2:
            crosstalk = 0.05
            for i in range(self.num_sensors):
                if i > 0:
                    values[i] += crosstalk * raw_values[i - 1]
                if i < self.num_sensors - 1:
                    values[i] += crosstalk * raw_values[i + 1]
            values = np.clip(values, 0.0, 1.0)

        self.sensor_readings = values

        # Usa thresholding: apenas sensores acima do limiar contribuem para o centróide
        # Isso evita que ruído de fundo ou bleed crie erro falso quando "fora da linha"
        thresholded = np.where(values > self.line_threshold, values, 0.0)
        total = float(thresholded.sum())

        if total > 1e-6:
            self.line_error = float(np.dot(self.sensor_weights, thresholded) / total)
            self.line_lost = False
        else:
            self.line_lost = True
            # Mantém o sinal do último erro válido para recuperação
            if abs(self.line_error) < 1e-6:
                self.line_error = self._last_sign

        # Atualiza _last_sign apenas quando a linha é efetivamente detectada
        if not self.line_lost and abs(self.line_error) > 1e-6:
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

    def clear_path(self):
        self.path.clear()

    # draw method removed - rendering is handled by frontend