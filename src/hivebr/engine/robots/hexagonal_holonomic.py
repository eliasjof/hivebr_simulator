from __future__ import annotations
import math
import numpy as np
import pygame
from .base import BaseRobot
from hivebr.engine.geometry import wrap_to_pi


class HexagonalHolonomicRobot(BaseRobot):
    """
    Holonomic robot with hexagonal shape and 3 omni wheels at 120 degrees.
    
    Wheel positions (aligned with hexagon sides, flat-top orientation):
        Wheel 1: 60°  (right-upper side)
        Wheel 2: 180° (left flat side / back)
        Wheel 3: 300° (right-lower side)
    
    Wheel tangent directions (velocity = tangent to circle = perpendicular to radius):
        Wheel 1 (60°):  tangent = 150°  (-sin 60°, cos 60°) = (-√3/2, 1/2)
        Wheel 2 (180°): tangent = 270°  (-sin 180°, cos 180°) = (0, -1)
        Wheel 3 (300°): tangent = 30°   (-sin 300°, cos 300°) = (√3/2, 1/2)
    
    Kinematics:
        [ẋ]   [ -r√3/2    0      r√3/2  ] [ω1]
        [ẏ] = [  r/2     -r      r/2    ] [ω2]
        [θ̇]   [ r/3L    r/3L    r/3L    ] [ω3]
    
    Where:
        r = wheel radius
        L = distance from robot center to wheel center
        ω1, ω2, ω3 = wheel angular velocities (rad/s)
    
    Control modes:
    1. Wheel speeds: {"omega1": float, "omega2": float, "omega3": float} - direct servo control
    2. Linear velocities: {"vx": float, "vy": float}
    3. Linear/angular: {"v": float, "omega": float}
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        c = config["robot"]
        
        # Pose
        self.initial_pose = np.array(c.get("initial_pose", [2.0, 2.0, 0.0]), dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()
        
        # Physical parameters
        self.radius = float(c.get("radius", 0.3))           # Robot radius (distance from center to wheel)
        self.wheel_radius = float(c.get("wheel_radius", 0.05))  # Wheel radius (r)
        self.max_wheel_speed = float(c.get("max_wheel_speed", 10.0))  # Max wheel angular velocity (rad/s)
        self.max_speed = float(c.get("max_speed", 2.0))     # Max linear speed (m/s)
        self.max_omega = float(c.get("max_omega", 4.0))     # Max angular speed (rad/s)
        
        # MG996R Servo parameters (optional, for realistic simulation)
        self.servo_max_speed = float(c.get("servo_max_speed", 6.28))  # ~60 RPM = 6.28 rad/s
        self.servo_torque = float(c.get("servo_torque", 1.5))         # Nm (stall torque at 6V)
        
        # Visual
        self.path_max_length = int(c.get("path_max_length", 4000))
        # Use config["colors"] directly so theme changes are reflected
        
        # Wheel velocities (rad/s)
        self.omega1 = 0.0
        self.omega2 = 0.0
        self.omega3 = 0.0
        
        # Robot velocities
        self.vx = 0.0
        self.vy = 0.0
        self.v = 0.0
        self.omega = 0.0
        
        # Precompute kinematic matrix
        self._compute_kinematic_matrices()
    
    def _compute_kinematic_matrices(self):
        """Precompute forward and inverse kinematic matrices."""
        r = self.wheel_radius
        L = self.radius
        sqrt3 = math.sqrt(3.0)
        
        # Forward kinematics: [vx, vy, omega]^T = J @ [ω1, ω2, ω3]^T
        # Wheels at 60°, 180°, 300° (aligned with hexagon sides)
        # Tangent vectors: (-sin φ, cos φ)
        # φ1=60°:  (-√3/2, 1/2)
        # φ2=180°: (0, -1)
        # φ3=300°: (√3/2, 1/2)
        # J = [ -r√3/2    0      r√3/2  ]
        #     [  r/2     -r      r/2    ]
        #     [ r/3L    r/3L    r/3L    ]
        self.J_fwd = np.array([
            [-r*sqrt3/2, 0, r*sqrt3/2],
            [r/2, -r, r/2],
            [r/(3*L), r/(3*L), r/(3*L)]
        ], dtype=float)
        
        # Inverse kinematics: [ω1, ω2, ω3]^T = J_inv @ [vx, vy, omega]^T
        self.J_inv = np.linalg.pinv(self.J_fwd)
    
    def set_initial_pose(self, x: float, y: float, theta: float = 0.0):
        self.initial_pose = np.array([x, y, theta], dtype=float)
        self.x, self.y, self.theta = self.initial_pose.tolist()
    
    @property
    def position(self):
        return np.array([self.x, self.y], dtype=float)
    
    def reset(self):
        self.x, self.y, self.theta = self.initial_pose.tolist()
        self.omega1 = self.omega2 = self.omega3 = 0.0
        self.vx = self.vy = 0.0
        self.v = self.omega = 0.0
        self.path.clear()
    
    def state(self):
        return {
            "type": "hexagonal_holonomic",
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "position": self.position.copy(),
            "vx": self.vx,
            "vy": self.vy,
            "v": self.v,
            "omega": self.omega,
            "omega1": self.omega1,
            "omega2": self.omega2,
            "omega3": self.omega3,
        }
    
    def _forward_kinematics(self, omega1: float, omega2: float, omega3: float):
        """Compute robot velocities from wheel speeds."""
        wheel_speeds = np.array([omega1, omega2, omega3])
        robot_vel = self.J_fwd @ wheel_speeds
        return robot_vel[0], robot_vel[1], robot_vel[2]
    
    def _inverse_kinematics(self, vx: float, vy: float, omega: float):
        """Compute wheel speeds from robot velocities."""
        robot_vel = np.array([vx, vy, omega])
        wheel_speeds = self.J_inv @ robot_vel
        return wheel_speeds[0], wheel_speeds[1], wheel_speeds[2]
    
    def _clamp_wheel_speeds(self, omega1: float, omega2: float, omega3: float):
        """Clamp wheel speeds to maximum."""
        max_ws = self.max_wheel_speed
        omega1 = max(-max_ws, min(max_ws, omega1))
        omega2 = max(-max_ws, min(max_ws, omega2))
        omega3 = max(-max_ws, min(max_ws, omega3))
        return omega1, omega2, omega3
    
    def _clamp_robot_velocities(self, vx: float, vy: float, omega: float):
        """Clamp robot velocities to maximum."""
        # Clamp linear velocity
        linear_speed = math.hypot(vx, vy)
        if linear_speed > self.max_speed:
            scale = self.max_speed / linear_speed
            vx *= scale
            vy *= scale
        
        # Clamp angular velocity
        omega = max(-self.max_omega, min(self.max_omega, omega))
        
        return vx, vy, omega
    
    def step(self, command: dict, dt: float):
        """
        Step the robot simulation.
        
        Command can be:
        - {"omega1": float, "omega2": float, "omega3": float} - Direct wheel control (servo mode)
        - {"vx": float, "vy": float} - Linear velocity control
        - {"v": float, "omega": float} - Linear + angular velocity control
        """
        # Detect control mode
        if "omega1" in command or "omega2" in command or "omega3" in command:
            # Mode 1: Direct wheel speed control (servo mode)
            omega1 = float(command.get("omega1", 0.0))
            omega2 = float(command.get("omega2", 0.0))
            omega3 = float(command.get("omega3", 0.0))
            
            # Clamp to servo limits
            omega1, omega2, omega3 = self._clamp_wheel_speeds(omega1, omega2, omega3)
            
            self.omega1, self.omega2, self.omega3 = omega1, omega2, omega3
            
            # Forward kinematics
            self.vx, self.vy, self.omega = self._forward_kinematics(omega1, omega2, omega3)
            self.v = math.hypot(self.vx, self.vy)
            
        elif "vx" in command or "vy" in command:
            # Mode 2: Linear velocity control (vx, vy)
            vx = float(command.get("vx", 0.0))
            vy = float(command.get("vy", 0.0))
            
            # Compute omega from vx, vy if theta is changing (holonomic can rotate while translating)
            # For pure holonomic, omega is independent
            omega = float(command.get("omega", 0.0))
            
            vx, vy, omega = self._clamp_robot_velocities(vx, vy, omega)
            
            self.vx, self.vy, self.omega = vx, vy, omega
            self.v = math.hypot(vx, vy)
            
            # Inverse kinematics to get wheel speeds
            self.omega1, self.omega2, self.omega3 = self._inverse_kinematics(vx, vy, omega)
            self.omega1, self.omega2, self.omega3 = self._clamp_wheel_speeds(
                self.omega1, self.omega2, self.omega3
            )
            
        elif "v" in command or "omega" in command:
            # Mode 3: Linear + angular velocity control (v, omega)
            v = float(command.get("v", 0.0))
            omega = float(command.get("omega", 0.0))
            
            # Convert to vx, vy in robot frame, then to world frame
            vx_robot = v
            vy_robot = 0.0
            
            # Transform to world frame
            cos_t = math.cos(self.theta)
            sin_t = math.sin(self.theta)
            vx = vx_robot * cos_t - vy_robot * sin_t
            vy = vx_robot * sin_t + vy_robot * cos_t
            
            vx, vy, omega = self._clamp_robot_velocities(vx, vy, omega)
            
            self.vx, self.vy, self.omega = vx, vy, omega
            self.v = math.hypot(vx, vy)
            
            # Inverse kinematics
            self.omega1, self.omega2, self.omega3 = self._inverse_kinematics(vx, vy, omega)
            self.omega1, self.omega2, self.omega3 = self._clamp_wheel_speeds(
                self.omega1, self.omega2, self.omega3
            )
        else:
            # No valid command, stop
            self.vx = self.vy = self.omega = 0.0
            self.v = 0.0
            self.omega1 = self.omega2 = self.omega3 = 0.0
        
        # Update pose
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.theta = wrap_to_pi(self.theta + self.omega * dt)
        
        # Record path
        self.path.append(self.position.copy())
        if len(self.path) > self.path_max_length:
            self.path.pop(0)
    
    def draw_path(self, screen, camera):
        if len(self.path) < 2:
            return
        pygame.draw.lines(screen, tuple(self.config["colors"]["path"]), False, 
                          [camera.world_to_screen(*p) for p in self.path], 2)
    
    def draw(self, screen, camera):
        # Draw path first
        self.draw_path(screen, camera)
        
        # Robot center in screen coordinates
        center = camera.world_to_screen(self.x, self.y)
        radius_px = max(5, int(self.radius * camera.scale))
        
        # Draw hexagonal body
        self._draw_hexagon(screen, camera)
        
        # Draw orientation indicator (front) - theme adaptive
        front = self.position + np.array([math.cos(self.theta), math.sin(self.theta)]) * self.radius * 1.2
        pygame.draw.line(screen, tuple(self.config["colors"]["white"]), center, 
                         camera.world_to_screen(*front), 3)
        
        # Draw 3 omni wheels at 120 degrees
        self._draw_wheels(screen, camera)
        
        # Draw wheel velocity indicators (optional debug)
        self._draw_wheel_velocities(screen, camera)
    
    def _draw_hexagon(self, screen, camera):
        """Draw hexagonal robot body."""
        colors = self.config["colors"]
        # Hexagon vertices (pointy top orientation)
        hex_vertices = []
        for i in range(6):
            angle = self.theta + i * math.pi / 3.0  # 60 degrees between vertices
            # Start at 90 degrees (pointy top)
            angle += math.pi / 6.0
            vx = self.x + self.radius * math.cos(angle)
            vy = self.y + self.radius * math.sin(angle)
            hex_vertices.append(camera.world_to_screen(vx, vy))
        
        # Draw filled hexagon
        pygame.draw.polygon(screen, tuple(colors["robot"]), hex_vertices)
        # Draw outline
        pygame.draw.polygon(screen, tuple(colors["black"]), hex_vertices, 2)
    
    def _draw_wheels(self, screen, camera):
        """Draw 3 omni wheels as rectangles (top-down view)."""
        colors = self.config["colors"]
        
        # Wheel dimensions in world units - LARGER WHEEL SIZE
        wheel_len = self.wheel_radius * 3.5   # length (along tangent) - increased more
        wheel_wid = self.wheel_radius * 0.8   # width (along radius) - slightly wider
        
        # Wheel positions at 60°, 180°, 300° (aligned with hexagon sides)
        wheel_angles = [
            self.theta + math.pi / 3,        # 60°  (right-upper side)
            self.theta + math.pi,            # 180° (left flat side / back)
            self.theta + 5 * math.pi / 3,    # 300° (right-lower side)
        ]
        
        # Wheel tangent directions (velocity directions = position + 90°)
        tangent_angles = [
            self.theta + 5 * math.pi / 6,    # 150° (60° + 90°)
            self.theta + 3 * math.pi / 2,    # 270° (180° + 90°)
            self.theta + math.pi / 6,        # 30°  (300° + 90° = 390° = 30°)
        ]
        
        wheel_colors = [
            (255, 100, 100),  # Red for wheel 1
            (100, 255, 100),  # Green for wheel 2
            (100, 100, 255),  # Blue for wheel 3
        ]
        
        # Theme-adaptive outline color
        outline_color = tuple(colors["black"])
        
        for i, (pos_angle, tang_angle) in enumerate(zip(wheel_angles, tangent_angles)):
            # Wheel center in world
            wx = self.x + self.radius * math.cos(pos_angle)
            wy = self.y + self.radius * math.sin(pos_angle)
            
            # Rectangle corners in local frame (aligned with tangent)
            cos_t = math.cos(tang_angle)
            sin_t = math.sin(tang_angle)
            cos_r = math.cos(pos_angle)
            sin_r = math.sin(pos_angle)
            
            half_len = wheel_len / 2
            half_wid = wheel_wid / 2
            
            # 4 corners: (±half_len along tangent, ±half_wid along radius)
            corners_local = np.array([
                [ half_len,  half_wid],
                [ half_len, -half_wid],
                [-half_len, -half_wid],
                [-half_len,  half_wid],
            ])
            
            # Rotate to world: tangent = x, radial = y
            rot_tangent = np.array([[cos_t, cos_r], [sin_t, sin_r]])
            corners_world = (rot_tangent @ corners_local.T).T + np.array([wx, wy])
            
            # Convert to screen
            corners_screen = [camera.world_to_screen(*c) for c in corners_world]
            
            # Draw wheel rectangle
            pygame.draw.polygon(screen, wheel_colors[i], corners_screen)
            pygame.draw.polygon(screen, outline_color, corners_screen, 2)
            
            # Draw roller lines (perpendicular to tangent = along radial)
            for j in range(3):
                offset = (j - 1) * half_len * 0.6
                sx = wx + (cos_t * offset + cos_r * half_wid * 0.8)
                sy = wy + (sin_t * offset + sin_r * half_wid * 0.8)
                ex = wx + (cos_t * offset - cos_r * half_wid * 0.8)
                ey = wy + (sin_t * offset - sin_r * half_wid * 0.8)
                pygame.draw.line(screen, (100, 100, 100), 
                                camera.world_to_screen(sx, sy), 
                                camera.world_to_screen(ex, ey), 2)
    
    def _draw_wheel_velocities(self, screen, camera):
        """Draw robot frame axes (X forward = theta, Y left = theta+90°)."""
        colors = self.config["colors"]
        
        # DEBUG: Draw robot frame axes (X forward = theta, Y left = theta+90°)
        robot_center = camera.world_to_screen(self.x, self.y)
        axis_len = self.radius * 1.5 * camera.scale
        # X axis (forward) - RED
        x_end = (robot_center[0] + axis_len * math.cos(self.theta),
                 robot_center[1] + axis_len * math.sin(self.theta))
        pygame.draw.line(screen, (255, 50, 50), robot_center, x_end, 3)
        pygame.draw.polygon(screen, (255, 50, 50), [
            x_end,
            (x_end[0] + 8 * math.cos(self.theta + math.pi * 0.7),
             x_end[1] + 8 * math.sin(self.theta + math.pi * 0.7)),
            (x_end[0] + 8 * math.cos(self.theta - math.pi * 0.7),
             x_end[1] + 8 * math.sin(self.theta - math.pi * 0.7))
        ])
        # Y axis (left) - GREEN
        y_end = (robot_center[0] + axis_len * math.cos(self.theta + math.pi/2),
                 robot_center[1] + axis_len * math.sin(self.theta + math.pi/2))
        pygame.draw.line(screen, (50, 255, 50), robot_center, y_end, 3)
        pygame.draw.polygon(screen, (50, 255, 50), [
            y_end,
            (y_end[0] + 8 * math.cos(self.theta + math.pi/2 + math.pi * 0.7),
             y_end[1] + 8 * math.sin(self.theta + math.pi/2 + math.pi * 0.7)),
            (y_end[0] + 8 * math.cos(self.theta + math.pi/2 - math.pi * 0.7),
             y_end[1] + 8 * math.sin(self.theta + math.pi/2 - math.pi * 0.7))
        ])
        # Labels
        font = pygame.font.SysFont("consolas", 10)
        x_label = font.render("X", True, (255, 50, 50))
        y_label = font.render("Y", True, (50, 255, 50))
        screen.blit(x_label, (x_end[0] + 5, x_end[1] - 5))
        screen.blit(y_label, (y_end[0] + 5, y_end[1] - 5))
    
    def get_wheel_speeds(self):
        """Return current wheel speeds in rad/s."""
        return self.omega1, self.omega2, self.omega3
    
    def set_wheel_speeds(self, omega1: float, omega2: float, omega3: float):
        """Directly set wheel speeds (for servo control)."""
        self.omega1, self.omega2, self.omega3 = self._clamp_wheel_speeds(omega1, omega2, omega3)
        self.vx, self.vy, self.omega = self._forward_kinematics(self.omega1, self.omega2, self.omega3)
        self.v = math.hypot(self.vx, self.vy)
    
    def set_robot_velocity(self, vx: float, vy: float, omega: float = 0.0):
        """Set robot velocity in world frame."""
        vx, vy, omega = self._clamp_robot_velocities(vx, vy, omega)
        self.vx, self.vy, self.omega = vx, vy, omega
        self.v = math.hypot(vx, vy)
        self.omega1, self.omega2, self.omega3 = self._inverse_kinematics(vx, vy, omega)
        self.omega1, self.omega2, self.omega3 = self._clamp_wheel_speeds(
            self.omega1, self.omega2, self.omega3
        )
    
    def set_robot_twist(self, v: float, omega: float):
        """Set robot velocity in robot frame (v forward, omega angular)."""
        vx_robot = v
        vy_robot = 0.0
        
        cos_t = math.cos(self.theta)
        sin_t = math.sin(self.theta)
        vx = vx_robot * cos_t - vy_robot * sin_t
        vy = vx_robot * sin_t + vy_robot * cos_t
        
        self.set_robot_velocity(vx, vy, omega)


# Factory function to register with the robot factory
def create_hexagonal_holonomic_robot(config: dict):
    return HexagonalHolonomicRobot(config)