from __future__ import annotations
import math
import numpy as np
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
        self.colors = config["colors"]
        
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
    
    def clear_path(self):
        self.path.clear()

    # draw_path and draw methods removed - rendering is handled by frontend
    
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