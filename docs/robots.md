# Robot Models

Every B-bot derives from `BaseRobot` and exposes a uniform interface:

| Member | Description |
| ------ | ----------- |
| `robot.position` | `numpy` array `[x, y]`. |
| `robot.x`, `robot.y`, `robot.theta` | Scalar pose. |
| `robot.state()` | Dictionary with type, pose, velocity and (for differential) battery. |
| `robot.step(command, dt)` | Advance the kinematics by one timestep. |
| `robot.reset()` | Return to the initial pose. |
| `robot.draw(screen, camera)` | Render the body. |

The **command** you return from a controller depends on the model.

## Supported Models

| `type` (aliases) | Command keys | Notes |
| ---------------- | ------------ | ----- |
| `differential` (`diff`, `unicycle`, `nonholonomic`) | `{"v": …, "omega": …}` | Classic unicycle, with optional battery model. |
| `differential_firstorder` (`firstorder`, `diff_tau`) | `{"v": …, "omega": …}` | Adds a first-order lag on the linear speed (`tau_v`). |
| `line_follower` (`line`, `linefollower`, `line_tracker`, `tcrt5000`) | `{"v": …, "omega": …}` | Differential kinematics + 2/5/8 analog line sensors (TCRT5000). |
| `holonomic` (`omni`, `omnidirectional`) | `{"vx": …, "vy": …}` | Velocity is set directly in world frame. |
| `hexagonal_holonomic` (`hexagonal`, `hex_holonomic`, `3wheel_holonomic`) | `{"omega1": …, "omega2": …, "omega3": …}` or `{"vx": …, "vy": …}` or `{"v": …, "omega": …}` | 3 omni-wheels at 120° (hexagon sides), direct servo control or world-frame velocity. |
| `ackermann` (`car`, `racecar`) | `{"speed": …, "steer": …}` | Bicycle model with front steering. |
| `boat` | `{"v": …, "omega": …}` | Like a differential drive, drawn as a hull. |

```python
# differential
return {"v": 0.5, "omega": 0.1}
# holonomic
return {"vx": 0.5, "vy": 0.0}
# ackermann
return {"speed": 0.5, "steer": 0.2}
# hexagonal holonomic - direct servo control
return {"omega1": 10.0, "omega2": -5.0, "omega3": 3.0}
# hexagonal holonomic - world frame velocity
return {"vx": 0.5, "vy": 0.2, "omega": 0.1}
```

## Kinematic Equations

### 1. Differential Drive (Unicycle)

**Command**: `{"v": v, "omega": ω}`

$$
\begin{aligned}
\dot{x} &= v \cos\theta \\
\dot{y} &= v \sin\theta \\
\dot{\theta} &= \omega
\end{aligned}
$$

**Parameters**:
- `max_speed`: max linear velocity (m/s)
- `max_omega`: max angular velocity (rad/s)
- `tau_v`: first-order lag time constant (s) — only for `differential_firstorder`

---

### 1b. Differential Drive (First-Order Lag)

**Command**: `{"v": v, "omega": ω}`

Same kinematics as differential drive, but with a first-order filter on the linear velocity command:

$$
\begin{aligned}
\dot{x} &= v_{\text{act}} \cos\theta \\
\dot{y} &= v_{\text{act}} \sin\theta \\
\dot{\theta} &= \omega \\
\tau_v \dot{v}_{\text{act}} + v_{\text{act}} &= v_{\text{cmd}}
\end{aligned}
$$

Where:
- $v_{\text{cmd}}$ = commanded linear velocity (from controller)
- $v_{\text{act}}$ = actual linear velocity (after lag)
- $\tau_v$ = time constant (`tau_v` config parameter)

**Parameters** (in addition to differential):
- `tau_v`: first-order velocity time constant (s)

---

### 2. Holonomic (Omnidirectional)

**Command**: `{"vx": v_x, "vy": v_y}` (world frame)

$$
\begin{aligned}
\dot{x} &= v_x \\
\dot{y} &= v_y \\
\dot{\theta} &= 0 \quad \text{(independent rotation not directly supported)}
\end{aligned}
$$

For rotation while translating, use world-frame `vx, vy` with appropriate values, or use `hexagonal_holonomic` which supports independent rotation.

---

### 3. Hexagonal Holonomic (3-Wheel Omni)

**Geometry**: 3 omni-wheels at 60°, 180°, 300° (aligned with hexagon flat sides, distance $L$ from center)

For an omni-wheel at angle $\phi$ (measured from +x axis), the **tangent direction** (direction of force/velocity applied to the ground) is perpendicular to the radius vector:

$$
\mathbf{t}(\phi) = \begin{bmatrix} -\sin\phi \\ \cos\phi \end{bmatrix}
$$

This gives the wheel tangent vectors:

| Wheel | Position $\phi$ | Tangent angle $\phi + 90^\circ$ | Tangent vector $\mathbf{t}$ |
|-------|-----------------|--------------------------------|----------------------------|
| 1 | $60^\circ$  | $150^\circ$ | $\begin{bmatrix} -\sin 60^\circ \\ \cos 60^\circ \end{bmatrix} = \begin{bmatrix} -\frac{\sqrt{3}}{2} \\ \frac{1}{2} \end{bmatrix}$ |
| 2 | $180^\circ$ | $270^\circ$ | $\begin{bmatrix} -\sin 180^\circ \\ \cos 180^\circ \end{bmatrix} = \begin{bmatrix} 0 \\ -1 \end{bmatrix}$ |
| 3 | $300^\circ$ | $30^\circ$  | $\begin{bmatrix} -\sin 300^\circ \\ \cos 300^\circ \end{bmatrix} = \begin{bmatrix} \frac{\sqrt{3}}{2} \\ \frac{1}{2} \end{bmatrix}$ |

#### Forward Kinematics

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

Where:
- $r$ = wheel radius (`wheel_radius`)
- $L$ = distance from robot center to wheel center (`radius`)
- $\omega_1, \omega_2, \omega_3$ = wheel angular velocities (rad/s)

#### Inverse Kinematics

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

#### Control Modes

| Mode | Command keys | Description |
|------|--------------|-------------|
| **Servo (direct)** | `omega1`, `omega2`, `omega3` | Direct wheel speed control (rad/s) |
| **World frame** | `vx`, `vy`, `omega` | World-frame linear + angular velocity |
| **Robot frame** | `v`, `omega` | Forward speed + angular velocity in robot frame |

**Parameters**:
- `radius`: robot radius (distance center → wheel) $L$ [m]
- `wheel_radius`: omni wheel radius $r$ [m]
- `max_wheel_speed`: max wheel angular velocity [rad/s]
- `max_speed`: max robot linear speed [m/s]
- `max_omega`: max robot angular speed [rad/s]
- `servo_max_speed`: max servo speed for control allocation [rad/s]

---

### 4. Ackermann (Car-like)

**Command**: `{"speed": v, "steer": \delta}`

$$
\begin{aligned}
\dot{x} &= v \cos\theta \\
\dot{y} &= v \sin\theta \\
\dot{\theta} &= \frac{v}{L} \tan\delta
\end{aligned}
$$

**Parameters**:
- `max_speed`: max linear velocity [m/s]
- `max_steer`: max steering angle [rad]
- `wheel_base`: distance between axles $L$ [m]

---

### 5. Boat

Same as differential drive kinematics, rendered as a boat hull.

---

### 6. Line Follower (TCRT5000)

**Command**: `{"v": v, "omega": ω}`

Uses the **same differential-drive kinematics** as the differential model:

$$
\begin{aligned}
\dot{x} &= v \cos\theta \\
\dot{y} &= v \sin\theta \\
\dot{\theta} &= \omega
\end{aligned}
$$

**Line Sensor Model**: The robot carries $N$ TCRT5000 analog sensors (typically $N \in \{2, 5, 8\}$) arranged linearly ahead of the body center. Each sensor returns a normalized reading $s_i \in [0, 1]$ where:
- $s_i \approx 1$ = over black line
- $s_i \approx 0$ = over white background

The **line position error** is computed as a weighted centroid:
$$
e = \frac{\sum_{i=1}^N w_i s_i}{\sum_{i=1}^N s_i} \in [-1, 1]
$$
where $w_i$ are lateral positions of sensors normalized to $[-1, 1]$.

**Parameters** (in addition to differential):
- `num_sensors`: number of TCRT5000 sensors (2, 5, or 8)
- `line_width`: physical line width [m]
- `sensor_offset`: distance from body center to sensor bar [m]
- `sensor_span`: total width of sensor array [m] (auto from `line_width` if omitted)
- `sensor_aperture`: sensing area radius [m]
- `sensor_noise`: Gaussian noise std on readings
- `line_threshold`: threshold for "on line" detection

---

## Selecting a Model

### Via YAML Config
```yaml
robot:
  type: hexagonal_holonomic
  radius: 0.3           # distance center to wheel (m)
  wheel_radius: 0.05    # wheel radius (m)
  max_wheel_speed: 20.0 # max wheel angular speed (rad/s)
  max_speed: 2.0        # max robot linear speed (m/s)
  max_omega: 4.0        # max robot angular speed (rad/s)
  servo_max_speed: 20.0 # max servo speed (rad/s)
```

### Programmatically
```python
sim = Simulator(config=config, controller=ctrl, type_robot="hexagonal_holonomic")
```

---

## Hexagonal Holonomic — Complete Example

### `examples/run_hexagonal_holonomic.py`

```python
from pathlib import Path
import sys
import math
import numpy as np
from hivebr.engine import Simulator, load_config

def servo_controller(robot, world, goal, config, dt, lidar_readings):
    """Direct servo control using inverse kinematics with control allocation."""
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
    
    # Control allocation: scale until wheels fit within servo limits
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

if __name__ == "__main__":
    config = load_config(ROOT / "config" / "hexagonal_holonomic.yaml")
    sim = Simulator(config=config, controller=servo_controller)
    sim.running_simulation = sim.config.get("running_simulation", False)
    sim.run()
```

### Configuration: `config/hexagonal_holonomic.yaml`

```yaml
window:
  width: 1400
  height: 750
  title: "HiveBr Simulator - Hexagonal Holonomic"

world:
  width: 20.0
  height: 12.0
  grid_size: 1.0

robot:
  type: hexagonal_holonomic
  initial_pose: [0.0, 0.0, 0.0]
  radius: 0.3              # Robot radius (L)
  wheel_radius: 0.05       # Wheel radius (r)
  max_wheel_speed: 20.0    # Max wheel angular velocity (rad/s)
  max_speed: 2.0           # Max linear speed (m/s)
  max_omega: 4.0           # Max angular speed (rad/s)
  servo_max_speed: 20.0    # Servo max speed (rad/s)

lidar:
  enabled: true
  num_rays: 36
  range: 5.0
  fov_deg: 360

waypoints:
  goal_tolerance: 0.15
  define_orientation: true
  show_tolerance_circle: true
  points:
    - [3.0, 2.0]
    - [5.0, -1.0]
    - [-2.0, -2.0]
    - [0.0, 0.0]

gui:
  sliders:
    - grid_size
    - noise_sigma
    - servo_max_speed    # Adjust max servo speed at runtime

theme: dark
```

Run with:
```bash
python examples/run_hexagonal_holonomic.py
```

---

## UI Sliders (Runtime Configuration)

The sidebar includes sliders to adjust robot parameters at runtime. Enable/disable via `config["gui"]["sliders"]`:

### Available Sliders

| Slider Key | Label | Config Path | Range | Applies To |
|------------|-------|-------------|-------|------------|
| `max_speed` | Max Speed | `robot.max_speed` | 0.2 – 8.0 | All except line_follower |
| `max_omega` | Max Omega | `robot.max_omega` | 0.1 – 6.0 | All except line_follower |
| `max_steer` | Max Steering | `robot.max_steer` | 0.1 – 1.2 | Ackermann |
| `grid_size` | Grid Size | `world.grid_size` | 0.1 – 5.0 | All |
| `noise_sigma` | Noise Sigma | `noise.sigma_v`, `noise.sigma_omega` | 0.0 – 1.0 | All (enables noise when > 0) |
| `servo_max_speed` | Max Servo Speed | `robot.servo_max_speed` | 0.5 – 30.0 | **Hexagonal Holonomic only** |

### Example: Enable Sliders in Config

```yaml
gui:
  buttons:
    - start
    - reset
    - clear_path
    - toggle_lidar
    - toggle_noise
    - toggle_theme
    - save_config
  sliders:
    - max_speed
    - max_omega
    - grid_size
    - noise_sigma
    - servo_max_speed    # Visible when robot is hexagonal_holonomic
```

### Using Sliders in Controller

```python
def controller(robot, world, goal, config, dt, lidar_readings):
    # Access runtime-adjusted values
    max_servo = robot.servo_max_speed  # Updated by slider
    max_speed = robot.max_speed        # Updated by slider
    
    # Your control logic here
    return {"omega1": ..., "omega2": ..., "omega3": ...}
```

---

## Line Follower (TCRT5000)

`LineFollowerRobot` keeps differential-drive kinematics but adds analog line sensors.

```yaml
world:
  line_map_image: config/line_track.png   # black line on white background
  resolution: 0.005                        # metres per pixel

robot:
  type: line_follower
  length: 0.10
  width: 0.10
  line_width: 0.02
  num_sensors: 5            # 2, 5 or 8 TCRT5000
  sensor_offset: 0.05
  sensor_aperture: 0.004
  sensor_noise: 0.0
  line_threshold: 0.5
```

Read sensors in controller:
```python
def controller(robot, world, goal, cfg, dt, lidar_readings=None):
    robot.read_line_sensors(world.line_map)
    error = robot.line_error          # -1 (right) .. +1 (left)
    return {"v": 0.3, "omega": 3.0 * error}
```

See `examples/line_follower.py` for full PID demo.

---

## Battery Model (Differential)

```python
robot.set_battery_parameters(
    c_idle=0.1,        # %/s at rest
    c_v=4.0,           # %/s per (m/s)²
    c_w=1.0,           # %/s per (rad/s)²
    critical_battery=50,
    working_battery=90,
)
```

---

## Building a Fleet

```yaml
robots:
  - type: differential
    initial_pose: [2.0, 2.0, 0.0]
    color: [30, 144, 255]
  - type: hexagonal_holonomic
    initial_pose: [-2.0, 2.0, 0.0]
    color: [220, 20, 60]
    radius: 0.3
    wheel_radius: 0.05
```

```python
from hivebr.engine import create_fleet
robots = create_fleet(config)   # list[BaseRobot]
```

---

## Custom Models

Subclass `BaseRobot` and implement `position`, `reset`, `state`, `step`, `draw`, then register in `hivebr.engine.robots.create_robot`.

```python
from hivebr.engine.robots.base import BaseRobot

class MyRobot(BaseRobot):
    @property
    def position(self):
        return np.array([self.x, self.y])

    def reset(self): ...
    def state(self): ...
    def step(self, command, dt): ...
    def draw(self, screen, camera): ...
```

See [API Reference](api/robots.md) for class documentation.