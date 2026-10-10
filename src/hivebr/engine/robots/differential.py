from __future__ import annotations
import math
import numpy as np
import pygame
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
            self.critical_battery  = float(c.get("critical_battery", 40.0))
            self.working_battery  = float(c.get("critical_battery", 90.0))
        self.going_to_recharge = False
            
    def set_charging(self):
        self.is_charging = True
        self.going_to_recharge = False

    def set_battery_parameters(self, c_idle, c_v, c_w, critical_battery=20, working_battery=90, battery_charge_rate=20):
        self.c_idle = float(c_idle)
        self.c_v = float(c_v)
        self.c_w = float(c_w)
        self.critical_battery = float(critical_battery)
        self.working_battery  = float(working_battery)
        self.enable_battery = True
        self.is_charging = False
        self.battery_charge_rate = battery_charge_rate
        
        print(f"Battery model enabled: c_idle={self.c_idle:.4f}, c_v={self.c_v:.4f}, c_w={self.c_w:.4f}, critical_battery={critical_battery:.2f} ")

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
        # Assuming power_motors_cruise = c_v_watts * v^2 + c_w_watts * omega^2
        # For simplicity, let's assume c_v_watts * v_cruise^2 takes a share, 
        # and we can estimate c_v and c_w. 
        # A simple approach: split motor power evenly between v and omega if both provided.
        
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

    def set_initial_pose(self,x,y,theta=0.0):
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

    def draw_path(self, screen, camera):
        if len(self.path) < 2:
            return
        pygame.draw.lines(screen, tuple(self.colors["path"]), False, [camera.world_to_screen(*p) for p in self.path], 2)

    def draw(self, screen, camera):
        center = camera.world_to_screen(self.x, self.y)
        radius_px = max(5, int(self.radius * camera.scale))
        pygame.draw.circle(screen, tuple(self.colors["robot"]), center, radius_px)
        front = self.position + np.array([math.cos(self.theta), math.sin(self.theta)]) * self.radius * 1.6
        pygame.draw.line(screen, tuple([192,192,186]), center, camera.world_to_screen(*front), 3)
        
        # =========================
        # Rodas
        # =========================
        wheel_len = self.radius * 0.8
        wheel_width = self.radius * 0.3
        
        rot = np.array([
            [math.cos(self.theta), -math.sin(self.theta)],
            [math.sin(self.theta),  math.cos(self.theta)]
        ])
        
        # Posições locais: centro das rodas em relação ao centro do robô
        # (x, y) = (0, +/- self.radius)
        # Vamos ajustar para ficarem um pouco para dentro
        offset = self.radius * 0.8
        
        wheels = [
            (0, offset),  # direita
            (0, -offset)  # esquerda
        ]
        
        for wx, wy in wheels:
            # centro da roda no mundo
            wheel_center = rot @ np.array([wx, wy]) + self.position
            
            # retângulo da roda
            # orientada na mesma direção que o robô para facilitar, ou perpendicular?
            # Para diferencial, rodas são paralelas ao eixo principal
            wheel_corners = np.array([
                [ wheel_len/2,  wheel_width/2],
                [ wheel_len/2, -wheel_width/2],
                [-wheel_len/2, -wheel_width/2],
                [-wheel_len/2,  wheel_width/2]
            ])
            
            # Rotacionar a roda (aqui alinhada com o corpo)
            wheel_pts = [
                camera.world_to_screen(*(rot @ c + wheel_center))
                for c in wheel_corners
            ]
            
            pygame.draw.polygon(
                screen,
                (139, 69, 19),
                wheel_pts
            )
        
        if self.enable_battery:
            # Draw battery indicator
            bar_width = radius_px * 1.2
            bar_height = radius_px * 0.4
            bar_x = center[0] - bar_width / 2
            bar_y = center[1] - bar_height / 2
            
            # Draw border
            pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)
            
            # Draw level
            fill_width = (self.battery_percent / 100.0) * (bar_width - 2)
            color = (0, 255, 0) if self.battery_percent > self.critical_battery else (255, 165, 0)
            if fill_width > 0:
                pygame.draw.rect(screen, color, (bar_x + 1, bar_y + 1, fill_width, bar_height - 2))
            
            # Draw text
            font = pygame.font.SysFont("Arial", int(radius_px * 0.5), bold=True)
            text = font.render(f"{int(self.battery_percent)}", True, (0, 0, 0))
            text_rect = text.get_rect(center=(center[0], center[1]))
            screen.blit(text, text_rect)
