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

## Supported models

| `type` (aliases) | Command keys | Notes |
| ---------------- | ------------ | ----- |
| `differential` (`diff`, `unicycle`, `nonholonomic`) | `{"v": …, "omega": …}` | Classic unicycle, with optional battery model. |
| `line_follower` (`line`, `linefollower`, `line_tracker`, `tcrt5000`) | `{"v": …, "omega": …}` | Differential kinematics + 2/5/8 analog line sensors (TCRT5000). |
| `differential_firstorder` (`firstorder`, `diff_tau`) | `{"v": …, "omega": …}` | Adds a first-order lag on the linear speed (`tau_v`). |
| `holonomic` (`omni`, `omnidirectional`) | `{"vx": …, "vy": …}` | Velocity is set directly in world frame. |
| `ackermann` (`car`, `racecar`) | `{"speed": …, "steer": …}` | Bicycle model with front steering. |
| `boat` | `{"v": …, "omega": …}` | Like a differential drive, drawn as a hull. |

```python
# differential
return {"v": 0.5, "omega": 0.1}
# holonomic
return {"vx": 0.5, "vy": 0.0}
# ackermann
return {"speed": 0.5, "steer": 0.2}
```

## Selecting a model

```yaml
robot:
  type: differential
```

or programmatically:

```python
sim = Simulator(config=config, controller=ctrl, type_robot="ackermann")
```

## Line follower (TCRT5000)

`LineFollowerRobot` keeps the differential-drive kinematics, but the body is a
square (default `10cm x 10cm`) carrying a horizontal bar of analog line sensors
in front. The line is *not* an obstacle: it is read from a **line map** — a
grayscale image whose dark pixels are the track (see
[`world.line_map_image`](configuration.md)).

```yaml
world:
  line_map_image: config/line_track.png   # black line on white background
  resolution: 0.005                        # metres per pixel

robot:
  type: line_follower
  length: 0.10
  width: 0.10
  line_width: 0.02          # physical line width (used to space the sensors)
  num_sensors: 5            # 2, 5 or 8 TCRT5000
  sensor_offset: 0.05       # distance ahead of the body centre
  # sensor_span: 0.08       # optional; derived from line_width when omitted
  sensor_aperture: 0.004    # sampled area radius
  sensor_noise: 0.0
  line_threshold: 0.5       # above this a sensor counts as "on the line"
```

Read the sensors from a control callback; each reading is analog in `[0, 1]`
(`1` = black line):

```python
def controller(robot, world, goal, cfg, dt, lidar_readings=None):
    robot.read_line_sensors(world.line_map)   # updates readings/error
    error = robot.line_error                  # -1 (right) .. +1 (left)
    return {"v": 0.3, "omega": 3.0 * error}
```

`robot.sensor_readings` holds the per-sensor values, `robot.line_position` is the
lateral offset in metres and `robot.line_lost` is `True` when no sensor sees the
line. If `sensor_span` is omitted it is derived from `line_width` so that the
line always crosses neighbouring sensors. See
`examples/line_follower.py` for a full PID demo on a random track.

### Lap timing and progress

The B-bot times itself while it follows the line. `reset_laps()` starts a new
measurement, and the running state is exposed through `robot.state()` and
`robot.lap_statistics()`:

```yaml
robot:
  lap_detection_radius: 0.15   # "back to start" radius for a closed track (m)
  min_lap_distance: 1.0        # min distance before a lap/finish is valid (m)
  min_lap_time: 1.0            # min lap duration (s)
  lost_timeout: 1.0            # line lost for this long => end of open track (s)
```

```python
stats = robot.lap_statistics()
# {"count": 3, "last": 12.84, "mean": 13.02, "best": 12.41, "worst": 13.55}
```

On a **closed** track the B-bot records a lap every time it returns near the
start; on an **open** track it declares `finished = True` and sets `finish_time`
after the line has been lost for `lost_timeout` seconds. `robot.state()` adds:
`line_error`, `line_lost`, `time`, `lap_count`, `lap_times`, `last_lap`,
`lap_avg`, `current_lap`, `finished` and `finish_time`.

### Comparing several line followers at once

You can run several `line_follower` B-bots on the **same track from the same
start point**, each with different gains, to compare techniques under identical
conditions. Because they start overlapped, turn off the robot–robot collision
evaluation so the B-bots do not stop on each other:

```python
config["interaction"] = {"collision_policy": "none", "robot_collision": False}
config["show_times"] = True     # show each B-bot's time in the HUD
```

Attach per-B-bot gains (the controller receives the B-bot object) and run one PID
per robot:

```python
for i, robot in enumerate(sim.robots):
    robot.pid_params = GAIN_SETS[i]     # e.g. {"kp": 4.0, "ki": 0.05, "kd": 0.9, ...}
```

After the run, each B-bot reports its own result:

```python
for i, robot in enumerate(sim.robots):
    print(f"B-Bot{i}: {robot.lap_statistics()}")
```

The **Toggle Times** button (or `config["show_times"]`) hides/shows the per-B-bot
timing in the HUD. See the
[Multi Line Follower example](examples/multi_line_follower.md) and the
[collision flag](multi_robot.md#robot-robot-interaction) for details. Pair this
with the [data logger](logging.md) to save the comparison.


## Battery model (differential)

Differential B-bots can model energy. It is disabled by default.

```python
robot.set_battery_parameters(
    c_idle=0.1,        # %/s at rest
    c_v=4.0,           # %/s per (m/s)^2
    c_w=1.0,           # %/s per (rad/s)^2
    critical_battery=50,
    working_battery=90,
)

# or derive coefficients from hardware specs:
robot.set_battery_parameters_from_specs(
    voltage=11.1, ah=5.0, power_electronics=1.0,
    power_motors_cruise=15.0, v_cruise=0.5,
)
```

Charging spots come from `world.recharge_places`. The engine charges a B-bot
while `robot.is_charging` is `True` and it sits within `goal_tolerance` of a
spot, until `battery_percent >= working_battery`.

## Building a fleet

`create_fleet(config)` reads `config["robots"]`; each spec overrides the base
`robot` block and may set a `color`.

```python
from hivebr.engine import create_fleet

robots = create_fleet(config)   # list[BaseRobot]
```

If `config["robots"]` is absent, a single B-bot is built from `config["robot"]`,
so **mono-robot is simply a fleet with N = 1**.

## Custom models

Subclass `BaseRobot` and implement `position`, `reset`, `state`, `step` and
`draw`, then add a branch in `hivebr.engine.robots.create_robot`:

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

See the API reference for [Robot classes](api/robots.md).
