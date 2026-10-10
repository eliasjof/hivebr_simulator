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
