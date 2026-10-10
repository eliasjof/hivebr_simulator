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
```

!!! note "Per-robot scans in a fleet"
    The engine stores one scan per B-bot in `sim.robot_lidar_readings`. A
    per-robot controller receives its own scan; `sim.lidar_readings` is a
    convenience alias for the **selected** B-bot.

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
