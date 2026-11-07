"""Line follower: a B-bot with TCRT5000 sensors and a PID controller.

Generates a random closed track (black line on a white background) in
config/line_track.png and puts the robot on it. The PID only uses the sensors.
How to use: the simulation starts by itself; lap times are printed to the console.
"""

import math

import numpy as np
from PIL import Image, ImageDraw

from hivebr.engine import Simulator, load_config
from hivebr.engine.geometry import clamp


def gera_pista(semente=7):
    """Draw the track on the image and return the line centre points (m)."""
    res = 0.005  # metres per pixel; 4 m x 3 m track
    rng = np.random.default_rng(semente)
    t = np.linspace(0.0, 2.0 * np.pi, 2000, endpoint=False)
    raio = np.ones_like(t)
    for k in (2, 3, 4):  # smooth ripples over an ellipse
        amplitude = rng.uniform(0.03, 0.08) / k
        fase = rng.uniform(0.0, 2.0 * np.pi)
        raio += amplitude * np.cos(k * t + fase)
    raio = np.clip(raio, 0.75, 1.05)
    xs = 2.0 + 1.44 * raio * np.cos(t)  # centre (2, 1.5) m; radii 1.44 m and 1.08 m
    ys = 1.5 + 1.08 * raio * np.sin(t)

    # In the image row 0 is at the top (largest world y): the y axis is flipped.
    h_px = round(3.0 / res)
    pontos = [(x / res, (h_px - 1) - y / res) for x, y in zip(xs, ys)]
    imagem = Image.new("RGB", (round(4.0 / res), h_px), (255, 255, 255))
    ImageDraw.Draw(imagem).line(pontos + [pontos[0]], fill=(0, 0, 0), width=4, joint="curve")  # 2 cm line
    imagem.save("config/line_track.png")
    return np.column_stack([xs, ys])


def controlador_pid(robot, world, goal, cfg, dt, lidar_readings=None):
    """Read the line sensors and return {"v", "omega"} from a PID."""
    robot.read_line_sensors(world.line_map)
    erro = robot.line_error  # -1: line on the right; +1: on the left; 0: centred
    pid = cfg["line_pid"]    # gains from config/line_follower.yaml

    if robot.line_lost:  # lost the line: turn towards the side of the last error
        robot._integral = 0.0
        return {"v": 0.1, "omega": 1.5 if erro >= 0 else -1.5}

    # Integral (clamped) and derivative of the error.
    integral = clamp(getattr(robot, "_integral", 0.0) + erro * dt,
                     -pid["integral_limit"], pid["integral_limit"])
    derivada = (erro - getattr(robot, "_erro_anterior", erro)) / dt
    robot._integral, robot._erro_anterior = integral, erro

    omega = pid["kp"] * erro + pid["ki"] * integral + pid["kd"] * derivada
    v = pid["base_speed"] * max(0.15, 1.0 - 0.6 * abs(erro))  # slower in the curves
    return {"v": v, "omega": clamp(omega, -robot.max_omega, robot.max_omega)}


if __name__ == "__main__":
    config = load_config("config/line_follower.yaml")
    pontos = gera_pista(semente=7)
    config["world"]["line_map_image"] = "config/line_track.png"  # use the freshly generated track

    # Initial pose: on the first point of the line, aligned with the next stretch.
    p0, p1 = pontos[0], pontos[12]
    sim = Simulator(config=config, controller=controlador_pid)
    sim.robot.set_initial_pose(float(p0[0]), float(p0[1]), math.atan2(p1[1] - p0[1], p1[0] - p0[0]))
    print(f"Sensors: {sim.robot.num_sensors}.")
    sim.run()

    stats = sim.robot.lap_statistics()
    if stats["count"]:
        print(f"Laps: {stats['count']} | best: {stats['best']:.2f} s | mean: {stats['mean']:.2f} s")
    else:
        print("No lap completed.")
