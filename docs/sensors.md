# Sensors

## LiDAR (2D)

The engine provides a configurable 2D LiDAR that ray-casts against both the
occupancy grid (DDA algorithm) and the analytic circular obstacles.

```yaml
lidar:
  enabled: true
  num_rays: 101
  range: 12.0
  fov_deg: 360
```

### Reading the scan

Inside a controller, the readings arrive as the last argument:

```python
def controller(robot, world, goal, cfg, dt, lidar_readings=None):
    if lidar_readings:
        angle, distance, hit_point = lidar_readings[0]   # first ray
```

Each reading is a tuple `(angle, distance, hit_point)`, where `angle` is in
world frame, `distance` is clamped to `range`, and `hit_point` is the world
coordinate of the hit.

You can also cast rays on demand:

```python
from hivebr.engine import Simulator, load_config

sim = Simulator(config=load_config("config/default.yaml"))
readings = sim.lidar.cast_rays(sim.robot, sim.world)
# include the other B-bots (with collision enabled) as moving obstacles:
readings = sim.lidar.cast_rays(sim.robot, sim.world, sim.lidar_obstacle_robots())
```

!!! note "Other B-bots as moving obstacles"
    When robot-robot collision is active (`interaction.robot_collision: true`,
    the default), the engine feeds the whole fleet to the LiDAR, so every B-bot
    is seen as a moving circular obstacle with its own radius. If you disable it
    (`robot_collision: false` or `collision_policy: none`), the LiDAR ignores the
    other B-bots. See [Multi-Robot Fleets](multi_robot.md#disabling-robot-robot-collision).

!!! note "Per-robot scans in a fleet"
    The engine stores one scan per B-bot in `sim.robot_lidar_readings`. A
    per-robot controller receives its own scan; `sim.lidar_readings` is a
    convenience alias for the **selected** B-bot.

## Line sensors (TCRT5000)

The `line_follower` B-bot carries an array of analog reflectance sensors
(TCRT5000) mounted in a horizontal bar in front of the body. The line is read
from a **line map**: a grayscale image whose dark pixels are the track. The
analog reading is `1.0` over the black line and `0.0` over the white background.

```python
values = robot.read_line_sensors(world.line_map)   # array in [0, 1]
error  = robot.line_error          # normalised lateral error in [-1, 1]
offset = robot.line_position       # lateral offset in metres
if robot.line_lost:
    ...                            # no sensor currently sees the line
```

### How `line_error` is computed

1. **Sample each sensor.** Sensor `i` sits at a local offset of
   `sensor_offset` ahead of the body centre and `y_i` sideways, with
   `y_i` spanning the bar from `-sensor_span/2` (the robot's right, `-y`) to
   `+sensor_span/2` (its left, `+y`). Each sensor reads the line map over a
   disk of radius `sensor_aperture` and returns an analog value
   `value_i` in `[0, 1]`.

2. **Weight the sensors** from right to left:

   ```text
   weights = linspace(-1, +1, num_sensors)
   # index 0 (y = -span/2, right) -> -1 ; last index (y = +span/2, left) -> +1
   ```

3. **Normalised, intensity-weighted centroid** — the error is the mean of the
   weights weighted by how strongly each sensor sees the line:

   ```text
   total      = sum(value_i)
   line_error = sum(weights_i * value_i) / total      # in [-1, +1]
   ```

   The sign convention is:

   - `line_error > 0` → the line is to the **left** of the robot (its centre of
     mass lies under the left sensors);
   - `line_error < 0` → the line is to the **right**;
   - `line_error = 0` → the line is centred (or symmetric under the bar);
   - `|line_error| = 1` → only the extreme sensor sees the line.

   Because a differential B-bot turns left with a positive `omega`, the natural
   controller is `{"v": base, "omega": kp * line_error}`.

4. **Metric offset.** Multiply by half the lateral span to get a distance:

   ```text
   line_position = line_error * (sensor_span / 2)      # metres, + = to the left
   ```

5. **Lost line.** If `total ~ 0` (no sensor sees the line) `line_lost` becomes
   `True` and `line_error` keeps the sign of the **last** non-zero error, so a
   controller can keep turning toward where the line was. That last sign is
   `_last_sign`, updated on every step where the line is still visible.

!!! tip "Choosing the number of sensors"
    Use 2, 5 or 8 sensors. With more sensors the weighted centroid resolves the
    lateral error more finely (smaller quantisation steps). If `sensor_span` is
    omitted it is derived from `line_width` so the line always crosses
    neighbouring sensors.

### What you have available

| Attribute / method | Description |
| ------------------ | ----------- |
| `robot.read_line_sensors(line_map)` | Samples the array and updates the fields below; returns the values. |
| `robot.sensor_readings` | `numpy` array in `[0, 1]`, one entry per sensor (`1` = line). |
| `robot.line_error` | Normalised lateral error in `[-1, +1]`; **positive = line to the left**. |
| `robot.line_position` | Lateral offset in **metres** (`line_error * sensor_span / 2`); positive = left. |
| `robot.line_lost` | `True` when no sensor sees the line (error keeps the last sign). |
| `robot.num_sensors` | Number of sensors. |
| `robot.sensor_offset` | Forward distance of the bar from the body centre (m). |
| `robot.sensor_span` | Total lateral span of the bar (m). |
| `robot.sensor_aperture` | Radius of the area sampled by each sensor (m). |
| `robot.sensor_weights` | The weights used in the centroid (`linspace(-1, 1, N)`). |
| `robot.sensor_local` | Local `(x, y)` of each sensor on the robot body. |
| `robot.sensor_world_position(i)` | World `(x, y)` of sensor `i`. |
| `robot.line_threshold` | Reading above which a sensor counts as "on the line". |

Configure the array under `robot` (`num_sensors`, `sensor_offset`,
`sensor_span`, `sensor_aperture`, `sensor_noise`, `line_width`). The line map is
loaded from `world.line_map_image` with `world.resolution`; it is rendered as the
arena background and does **not** participate in collision checks. See
[Robot Models](robots.md) and `examples/line_follower.py`.

## Adding your own sensor

Sensors are plain objects that read from a robot and the world. A minimal
sensor that returns the distance to the nearest obstacle:

```python
class RangeSensor:
    def __init__(self, max_range=5.0):
        self.max_range = max_range

    def read(self, robot, world):
        d = world.distance_to_nearest_obstacle(robot.position)
        return min(d, self.max_range)
```

Wire it into your controller closure, or extend `Simulator` to store readings
alongside `robot_lidar_readings`.

See the [LiDAR API reference](api/lidar.md).
