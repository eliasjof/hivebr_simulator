# Single Robot — Hexagonal Holonomic (3-Wheel Omni)

Reference: [`examples/run_hexagonal_holonomic.py`](https://github.com/eliasjof/hivebr_simulator/blob/main/examples/run_hexagonal_holonomic.py)

A hexagonal holonomic robot with 3 omni-wheels at 120° (aligned with hexagon sides), controlled via **inverse kinematics with control allocation** to convert world-frame velocity commands into individual wheel speeds.

## What it shows

- The `hexagonal_holonomic` robot model with direct servo control
- Inverse kinematics to convert `(vx, vy, ω)` → `(ω₁, ω₂, ω₃)`
- Control allocation to respect servo speed limits
- Waypoint navigation with orientation

## Kinematics

**Wheel geometry**: 3 omni-wheels at 60°, 180°, 300° (flat hexagon sides, distance $L$ from center)

For an omni-wheel at angle $\phi$, the tangent direction (force/velocity applied to ground) is perpendicular to the radius:

$$
\mathbf{t}(\phi) = \begin{bmatrix} -\sin\phi \\ \cos\phi \end{bmatrix}
$$

| Wheel | Position $\phi$ | Tangent angle $\phi + 90^\circ$ | Tangent vector $\mathbf{t}$ |
|-------|-----------------|--------------------------------|----------------------------|
| 1 | $60^\circ$  | $150^\circ$ | $\begin{bmatrix} -\sin 60^\circ \\ \cos 60^\circ \end{bmatrix} = \begin{bmatrix} -\frac{\sqrt{3}}{2} \\ \frac{1}{2} \end{bmatrix}$ |
| 2 | $180^\circ$ | $270^\circ$ | $\begin{bmatrix} -\sin 180^\circ \\ \cos 180^\circ \end{bmatrix} = \begin{bmatrix} 0 \\ -1 \end{bmatrix}$ |
| 3 | $300^\circ$ | $30^\circ$  | $\begin{bmatrix} -\sin 300^\circ \\ \cos 300^\circ \end{bmatrix} = \begin{bmatrix} \frac{\sqrt{3}}{2} \\ \frac{1}{2} \end{bmatrix}$ |

**Forward kinematics** (wheel speeds $\omega_i$ → robot velocity):

$$
\begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\theta} \end{bmatrix}
=
\underbrace{\begin{bmatrix}
-r\frac{\sqrt{3}}{2} & 0 & r\frac{\sqrt{3}}{2} \\[4pt]
\frac{r}{2} & -r & \frac{r}{2} \\[4pt]
\frac{r}{3L} & \frac{r}{3L} & \frac{r}{3L}
\end{bmatrix}}_{\mathbf{J}_f}
\begin{bmatrix} \omega_1 \\ \omega_2 \\ \omega_3 \end{bmatrix}
$$

**Inverse kinematics** (robot velocity → wheel speeds):

$$
\begin{bmatrix} \omega_1 \\ \omega_2 \\ \omega_3 \end{bmatrix}
=
\mathbf{J}_f^{\dagger}
\begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\theta} \end{bmatrix}
=
\begin{bmatrix}
-\frac{2}{3r} & \frac{\sqrt{3}}{3r} & \frac{L}{r} \\[4pt]
-\frac{2}{3r} & -\frac{\sqrt{3}}{3r} & \frac{L}{r} \\[4pt]
\frac{4}{3r} & 0 & \frac{L}{r}
\end{bmatrix}
\begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\theta} \end{bmatrix}
$$

Where $r$ = wheel radius, $L$ = robot radius (center to wheel).

## Key Parts

```python
def servo_controller(robot, world, goal, config, dt, lidar_readings):
    if goal is None:
        return {"omega1": 0.0, "omega2": 0.0, "omega3": 0.0}
    
    goal_pos = np.array(goal[:2])
    pos = robot.position
    to_goal = goal_pos - pos
    dist = np.linalg.norm(to_goal)
    
    tolerance = 0.15
    if dist < tolerance:
        return {"omega1": 0.0, "omega2": 0.0, "omega3": 0.0}
    
    # World-frame velocity control
    kv = 2.0
    vx_des = kv * to_goal[0]
    vy_des = kv * to_goal[1]
    
    # Limit linear speed
    speed = math.hypot(vx_des, vy_des)
    if speed > robot.max_speed:
        scale = robot.max_speed / speed
        vx_des *= scale
        vy_des *= scale
    
    # Angular velocity to align with goal
    goal_angle = math.atan2(to_goal[1], to_goal[0])
    angle_diff = (goal_angle - robot.theta + math.pi) % (2 * math.pi) - math.pi
    kw = 3.0
    omega_des = kw * angle_diff
    omega_des = max(-robot.max_omega, min(robot.max_omega, omega_des))
    
    # Control allocation: scale down until wheels fit within servo limits
    max_servo = robot.servo_max_speed
    
    for _ in range(5):
        omega1, omega2, omega3 = robot._inverse_kinematics(vx_des, vy_des, omega_des)
        max_wheel = max(abs(omega1), abs(omega2), abs(omega3))
        if max_wheel <= max_servo:
            break
        scale = max_servo / max_wheel
        vx_des *= scale
        vy_des *= scale
        omega_des *= scale
    
    # Final inverse kinematics
    omega1, omega2, omega3 = robot._inverse_kinematics(vx_des, vy_des, omega_des)
    
    # Final clamp
    omega1 = max(-max_servo, min(max_servo, omega1))
    omega2 = max(-max_servo, min(max_servo, omega2))
    omega3 = max(-max_servo, min(max_servo, omega3))
    
    return {"omega1": omega1, "omega2": omega2, "omega3": omega3}
```

## Configuration

```yaml
robot:
  type: hexagonal_holonomic
  initial_pose: [0.0, 0.0, 0.0]
  radius: 0.3              # L: distance center to wheel (m)
  wheel_radius: 0.05       # r: wheel radius (m)
  max_wheel_speed: 20.0    # Max wheel angular velocity (rad/s)
  max_speed: 2.0           # Max robot linear speed (m/s)
  max_omega: 4.0           # Max robot angular speed (rad/s)
  servo_max_speed: 20.0    # Servo limit for control allocation (rad/s)
```

## Run It

```bash
python examples/run_hexagonal_holonomic.py
```

## UI Sliders

The sidebar includes a **Max Servo Speed** slider (`servo_max_speed`) when the robot is `hexagonal_holonomic`. This lets you tune the servo limit at runtime for control allocation.

```yaml
gui:
  sliders:
    - grid_size
    - noise_sigma
    - servo_max_speed    # Only for hexagonal_holonomic
```

## Visualization

The robot renders as a hexagon with 3 colored omni-wheels at the flat sides:
- **Red** = Wheel 1 (60°)
- **Green** = Wheel 2 (180°)  
- **Blue** = Wheel 3 (300°)

Robot frame axes:
- **Red X** = Forward direction (θ)
- **Green Y** = Left direction (θ + 90°)

## Full Source

```python title="examples/run_hexagonal_holonomic.py"
--8<-- "examples/run_hexagonal_holonomic.py"
```

Next: Try the [Multi-Robot Fleet example](multi_robot.md) to mix holonomic and differential B-bots.