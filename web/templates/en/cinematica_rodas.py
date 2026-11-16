"""Activity: wheel kinematics of a differential robot.

The controller decides (v, omega), but the motors receive wheel angular
speeds. Complete velocidades_rodas() with the inverse kinematics:

    wl = (v - omega * base / 2) / raio
    wr = (v + omega * base / 2) / raio

The controller converts the wheels back to (v, omega) and drives the robot from
(2, 2) to (12, 8). The console must print TUDO CERTO.
"""

import math

from hivebr.engine import Simulator, load_config

ALVO = (12.0, 8.0)
BASE = 0.285
RAIO = 0.05
VMAX = 1.2
KP_DIST = 1.4
KP_ANG = 3.5
TOLERANCIA = 0.10


def normaliza(angulo):
    return math.atan2(math.sin(angulo), math.cos(angulo))


def velocidades_rodas(v, omega, base, raio):
    """Return (left_wheel, right_wheel) in rad/s."""
    # TODO: apply the differential inverse kinematics.
    raise NotImplementedError


def controlador(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    dx = goal[0] - robot.x
    dy = goal[1] - robot.y
    distancia = math.hypot(dx, dy)
    if distancia < TOLERANCIA:
        return {"v": 0.0, "omega": 0.0}

    erro = normaliza(math.atan2(dy, dx) - robot.theta)
    v = min(VMAX, KP_DIST * distancia) * max(0.0, math.cos(erro))
    omega = KP_ANG * erro

    wl, wr = velocidades_rodas(v, omega, BASE, RAIO)
    v_rec = (wl + wr) * RAIO / 2.0
    omega_rec = (wr - wl) * RAIO / BASE
    return {"v": v_rec, "omega": omega_rec}


def rodar(sim, limite=60.0):
    while sim.running:
        sim.step()
        if not sim.waypoints.has_waypoint() or sim.sim_time > limite:
            sim.running = False


if __name__ == "__main__":
    wl, wr = velocidades_rodas(1.0, 0.0, BASE, RAIO)
    assert abs(wl - 1.0 / RAIO) < 1e-9
    assert abs(wr - 1.0 / RAIO) < 1e-9
    wl, wr = velocidades_rodas(0.5, 1.0, BASE, RAIO)
    assert wl < wr

    config = load_config("config/default.yaml")
    config["world"]["obstacles"] = []
    config["obstacles"] = []
    config["robot"]["initial_pose"] = [2.0, 2.0, 0.0]
    config["waypoints"]["goal_tolerance"] = 0.20

    sim = Simulator(config=config, controller=controlador)
    sim.set_robot_waypoints(0, [(ALVO[0], ALVO[1], math.nan)])

    print(f"Target: {ALVO}")
    rodar(sim)
    print(f"Final position: ({sim.robot.x:.2f}, {sim.robot.y:.2f})")
    if math.hypot(sim.robot.x - ALVO[0], sim.robot.y - ALVO[1]) < 0.3:
        print("TUDO CERTO")
    print("Simulation finished.")
