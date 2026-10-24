# Configuration

A configuration is a plain dictionary. The engine ships with a default
(`hivebr.engine.simulator.DEFAULT_CONFIG`) and examples usually load
`config/default.yaml` with `load_config`.

## Full example

```yaml
window:
  width: 1400
  height: 750
  min_width: 1100
  min_height: 650
  panel_width: 300
  title: "hivebr"

world:
  width: 20.0
  height: 12.0
  grid_size: 1.0
  obstacle_radius: 0.4
  show_origin: true
  show_axes: true
  show_inflation: true
  # map_image: "maze.png"     # optional occupancy-grid map
  # resolution: 0.1           # metres per pixel
  recharge_places:
    - [3, 3]
    - [5, 5]

camera:
  initial_zoom: 1.0
  min_zoom: 0.25
  max_zoom: 8.0
  zoom_step: 1.1
  margin_x: 1.0
  margin_y: 1.0

# Default B-bot (used directly for N = 1, and as base for the fleet)
robot:
  type: differential
  initial_pose: [2.5, 2.5, 0.0]
  radius: 0.1375
  length: 0.39
  width: 0.275
  wheel_base: 0.285
  max_speed: 3.0
  max_omega: 4.0
  max_steer: 0.52
  tau_v: 0.2                 # first-order motor time constant
  path_max_length: 4000

# Optional fleet: each entry overrides `robot` and may carry a color
robots:
  - { id: 0, type: differential, initial_pose: [2.0, 2.0, 0.0], radius: 0.25 }
  - { id: 1, type: differential, initial_pose: [5.0, 5.0, 0.0], radius: 0.25,
      color: [220, 20, 60] }

lidar:
  enabled: false
  num_rays: 101
  range: 12.0
  fov_deg: 360

# Gaussian actuation noise on the commanded velocities
noise:
  enabled: false
  sigma_v: 0.0               # std of the linear velocity error (m/s)
  sigma_omega: 0.0           # std of the angular velocity error (rad/s)
  limit: 3.0                 # truncate the error at +/- limit * sigma
  seed: null                 # optional RNG seed for reproducibility

waypoints:
  goal_tolerance: 0.5
  define_orientation: true
  show_tolerance_circle: false
  points: []                 # global list, applied to B-bot 0

interaction:
  collision_policy: stop     # "stop" | "resolve" | "none"
  robot_collision: true      # master switch for robot-robot collision checks
  robot_safety_margin: 0.0
  resolve_push: 0.05
  comm_radius: null          # null = full visibility
  show_robot_links: false

show_times: true             # HUD per-B-bot timing (line followers)

obstacles:
  - { x: 6.0, y: 5.0, radius: 1.2 }

colors:
  background: [30, 30, 30]
  robot: [30, 144, 255]
  fleet:
    - [30, 144, 255]
    - [220, 20, 60]
    - [50, 205, 50]
    - [255, 165, 0]
    - [148, 0, 211]
    - [0, 206, 209]
    - [255, 105, 180]
    - [255, 215, 0]

theme: dark                  # "dark" | "light"
```

## Section reference

| Section | Key | Meaning |
| ------- | --- | ------- |
| `window` | `width`, `height` | Initial window size in pixels. |
| | `min_width`, `min_height` | Lower bound when resizing. |
| | `panel_width` | Width of the right control panel. |
| `world` | `width`, `height` | World size in metres. |
| | `grid_size` | Background grid spacing. |
| | `obstacle_radius` | Default radius for mouse-added obstacles. |
| | `map_image`, `resolution` | Occupancy-grid source image and metres/pixel. |
| | `line_map_image` | Line-follower track image (black line on white), rendered as background. |
| | `recharge_places` | Charging spots (`[x, y]` or `[x, y, r]`). |
| `camera` | `initial_zoom`, `min_zoom`, `max_zoom` | Zoom limits. |
| `robot` | `type` | Kinematic model (see [Robot Models](robots.md)). |
| | `initial_pose` | `[x, y, theta]` spawn pose. |
| | `radius` | Collision radius (for differential/ackermann/boat). For hexagonal_holonomic: distance from center to wheel center `L` (m). |
| | `wheel_radius` | (hexagonal_holonomic) Wheel radius `r` (m). |
| | `max_wheel_speed` | (hexagonal_holonomic) Max wheel angular velocity (rad/s). |
| | `max_speed`, `max_omega`, `max_steer` | Actuation limits. |
| | `tau_v` | First-order velocity time constant. |
| | `servo_max_speed` | (hexagonal_holonomic) Max servo speed for control allocation (rad/s). |
| | `num_sensors`, `line_width`, `sensor_offset`, `sensor_span`, `sensor_aperture`, `sensor_noise`, `line_threshold` | Line-follower TCRT5000 array. |
| | `lap_detection_radius`, `min_lap_distance`, `min_lap_time`, `lost_timeout` | Line-follower lap timing / end-of-track detection. |
| `robots` | list of specs | Fleet; each overrides `robot` and may set `color`. |
| `lidar` | `enabled`, `num_rays`, `range`, `fov_deg` | Sensor settings. |
| `noise` | `enabled` | Inject Gaussian noise on the actuated velocities. |
| | `sigma_v`, `sigma_omega` | Std of the linear / angular velocity error. |
| | `sigma` | Alias applied to both `sigma_v` and `sigma_omega`. |
| | `limit` | Truncate the sampled error at `+/- limit * sigma`. |
| | `seed` | Optional RNG seed (reproducible runs). |
| `waypoints` | `goal_tolerance` | Distance to consider a waypoint reached. |
| | `define_orientation` | Ask for a final heading when adding waypoints. |
| `interaction` | `collision_policy` | `stop`, `resolve` or `none` for B-bot pairs. |
| | `robot_collision` | Master switch; `false` disables robot-robot collision checks entirely. |
| | `robot_safety_margin` | Extra separation added to `r_i + r_j`. |
| | `comm_radius` | Visibility radius for decentralized neighbors. |
| | `show_robot_links` | Draw communication links between neighbors. |
| `show_times` | | Show per-B-bot timing in the HUD (toggled by **Toggle Times**). |
| `theme` | | `dark` or `light` palette. |
| `gui` | `buttons` | List of sidebar buttons to show (see below). |
| | `sliders` | List of sidebar sliders to show (see below). |

### GUI Buttons (optional)

Control which buttons appear in the right sidebar. Default shows all.

| Key | Button | Description |
|-----|--------|-------------|
| `start` | Start / Pause | Toggle simulation |
| `reset` | Reset | Reset robot poses |
| `clear_path` | Clear Path | Erase drawn path |
| `clear_waypoints` | Clear Waypoints | Remove all waypoints |
| `clear_obstacles` | Clear Obstacles | Remove all obstacles |
| `load_map` | Load Map | Open file dialog for map image |
| `draw_track` | Draw Track | Enable track drawing mode |
| `apply_track` | Apply Track | Save drawn track |
| `clear_track` | Clear Track | Erase drawn track |
| `toggle_lidar` | Toggle LiDAR | Enable/disable LiDAR |
| `toggle_noise` | Toggle Noise | Enable/disable actuation noise |
| `toggle_times` | Toggle Times | Show/hide per-robot timing |
| `toggle_theme` | Toggle Theme | Switch dark/light |
| `save_config` | Save Config | Save current config to YAML |
| `center_camera` | Center Camera | Reset camera view |
| `plot_log` | Plot Log | Plot data logger |
| `export_log` | Export Log | Save log to file |
| `reset_logger` | Reset Logger | Clear logger data |

Example:
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
```

### GUI Sliders (optional)

Control which parameter sliders appear in the right sidebar. Default shows common sliders.

| Key | Slider | Config Path | Range | Applies To |
|-----|--------|-------------|-------|------------|
| `max_speed` | Max Speed | `robot.max_speed` | 0.2 – 8.0 | All except line_follower |
| `max_omega` | Max Omega | `robot.max_omega` | 0.1 – 6.0 | All except line_follower |
| `max_steer` | Max Steering | `robot.max_steer` | 0.1 – 1.2 | Ackermann |
| `grid_size` | Grid Size | `world.grid_size` | 0.1 – 5.0 | All |
| `noise_sigma` | Noise Sigma | `noise.sigma_v`, `noise.sigma_omega` | 0.0 – 1.0 | All |
| `servo_max_speed` | Max Servo Speed | `robot.servo_max_speed` | 0.5 – 30.0 | **Hexagonal Holonomic** |

Example:
```yaml
gui:
  sliders:
    - max_speed
    - max_omega
    - grid_size
    - noise_sigma
    - servo_max_speed
```

!!! note "Mono is fleet with N = 1"
    If `robots` is omitted, the engine builds a single B-bot from `robot`.
    Adding `robots` is the only change needed to go multi-robot.
