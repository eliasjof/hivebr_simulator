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
robot.read_line_sensors(world.line_map)
values = robot.sensor_readings     # array in [0, 1], one entry per sensor
error  = robot.line_error          # normalised lateral error in [-1, 1]
offset = robot.line_position       # lateral offset in metres
if robot.line_lost:
    ...                            # no sensor currently sees the line
```

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
