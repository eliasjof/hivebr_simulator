from __future__ import annotations
import math
import numpy as np
from .base import BaseRobot
from hivebr.engine.geometry import wrap_to_pi, clamp


class DifferentialRobot(BaseRobot):
    def __init__(self, config: dict):
        super().__init__(config)
        c = config["robot"]
        self.initial_pose = np.array(c.get("initial_pose", [2.0, 2.0, 0.0]), dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.radius = float(c.get("radius", 0.3))
        self.max_speed = float(c.get("max_speed", 2.0))
        self.max_omega = float(c.get("max_omega", 2.0))
        self.path_max_length = int(c.get("path_max_length", 4000))
        self.v = 0.0
        self.omega = 0.0
        self.colors = config["colors"]
        self.battery_percent = 100.0
        self.is_charging = False
        self.battery_charge_rate = float(c.get("battery_charge_rate", 20.0))
        self.enable_battery = bool(c.get("enable_battery", False))
        if self.enable_battery:
            self.c_idle = float(c.get("c_idle", 0.01))
            self.c_v = float(c.get("c_v", 0.05))
            self.c_w = float(c.get("c_w", 0.02))
            self.critical_battery = float(c.get("critical_battery", 40.0))
            self.working_battery = float(c.get("critical_battery", 90.0))
        self.going_to_recharge = False

    def set_charging(self):
        self.is_charging = True
        self.going_to_recharge = False

    def set_battery_parameters(self, c_idle, c_v, c_w, critical_battery=20, working_battery=90, battery_charge_rate=20):
        self.c_idle = float(c_idle)
        self.c_v = float(c_v)
        self.c_w = float(c_w)
        self.critical_battery = float(critical_battery)
        self.working_battery = float(working_battery)
        self.enable_battery = True
        self.is_charging = False
        self.battery_charge_rate = battery_charge_rate

    def set_battery_parameters_from_specs(self, voltage, ah, power_electronics, power_motors_cruise, v_cruise, omega_cruise=0.0):
        """
        Calculates battery consumption coefficients from physical specifications.
        E_total = V * Ah * 3600 (Joules)
        Consumption (%/s) = (Power (W) / E_total) * 100
        """
        energy_joules = voltage * ah * 3600

        # Power idle (electronics)
        p_idle = power_electronics
        c_idle = (p_idle / energy_joules) * 100

        # Power motors (cruise)
        motor_power = power_motors_cruise
        c_v = 0.0
        c_w = 0.0

        if v_cruise > 0 and omega_cruise > 0:
            c_v_watts = (motor_power / 2) / (v_cruise**2)
            c_w_watts = (motor_power / 2) / (omega_cruise**2)
            c_v = (c_v_watts / energy_joules) * 100
            c_w = (c_w_watts / energy_joules) * 100
        elif v_cruise > 0:
            c_v_watts = motor_power / (v_cruise**2)
            c_v = (c_v_watts / energy_joules) * 100
        elif omega_cruise > 0:
            c_w_watts = motor_power / (omega_cruise**2)
            c_w = (c_w_watts / energy_joules) * 100

        self.set_battery_parameters(c_idle, c_v, c_w)
        return self.battery_percent

    def update_battery(self, dt: float, charge_rate: float = 10.0):
        """
        Updates battery level. If charging is True, increases battery at charge_rate (%/s).
        """
        if not self.enable_battery:
            return

        if self.is_charging:
            self.battery_percent = min(100.0, self.battery_percent + charge_rate * dt)
            if self.battery_percent >= self.working_battery:
                self.is_charging = False
        else:
            consumption = (
                self.c_idle
                + self.c_v * self.v**2
                + self.c_w * self.omega**2
            )
            self.battery_percent = max(0.0, self.battery_percent - consumption * dt)

    def enable_battery(self, enable=True):
        self.enable_battery = enable

    def set_initial_pose(self, x, y, theta=0.0):
        self.initial_pose = np.array([x, y, theta], dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()

    @property
    def position(self):
        return np.array([self.x, self.y], dtype=float)

    def reset(self):
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.v = 0.0
        self.omega = 0.0
        self.path.clear()
        self.battery_percent = 100

    def state(self):
        return {"type": "differential", "x": self.x, "y": self.y, "theta": self.theta, "position": self.position.copy(), "v": self.v, "omega": self.omega}

    def step(self, command: dict, dt: float):
        if self.enable_battery and self.battery_percent <= 0:
            self.v = 0.0
            self.omega = 0.0
        else:
            self.v = clamp(float(command.get("v", 0.0)), -self.max_speed, self.max_speed)
            self.omega = clamp(float(command.get("omega", 0.0)), -self.max_omega, self.max_omega)

        self.update_battery(dt)

        self.x += self.v * math.cos(self.theta) * dt
        self.y += self.v * math.sin(self.theta) * dt
        self.theta = wrap_to_pi(self.theta + self.omega * dt)
        self.path.append(self.position.copy())
        if len(self.path) > self.path_max_length:
            self.path.pop(0)

    def clear_path(self):
        self.path.clear()

    # draw_path and draw methods removed - rendering is handled by frontend