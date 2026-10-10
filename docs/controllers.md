# Controllers

A **controller** maps the current situation to a velocity command. In the
low-level engine it is any callable with this signature:

```python
def controller(robot, world, goal, config, dt, lidar_readings=None) -> dict:
    ...
```

- `robot` — the B-bot being controlled (has `.x`, `.y`, `.theta`, `.position`,
  `.max_speed`, `.max_omega`, …).
- `world` — the environment (`.obstacles`, `.grid_map`, `.recharge_places`).
- `goal` — the current waypoint `[x, y, theta]` or `None`.
- `config` — the full configuration dictionary.
- `dt` — timestep in seconds.
- `lidar_readings` — list of `(angle, distance, hit)` tuples.

The engine also accepts 5-argument controllers (without `lidar_readings`) and
falls back automatically.

!!! tip "High-level API"
    With `HiveBrAgent` you implement `loop(state, neighbors)` instead, where the
    goal arrives inside `state.goal`. See the [OpenLab API](openlab_api.md).

## Controllers shipped in `examples/controllers`

| Controller | Import | Idea |
| ---------- | ------ | ---- |
| `potential_field_controller` | `examples.controllers.potential_field` | Artificial potential fields with collision-recovery FSM, local-minima detection, virtual subgoals and tangential repulsion. |
| `potential_field_controller` | `examples.controllers.potential_field2` | Lighter potential-field variant. |
| `vortex_apf_controller` | `examples.controllers.vortex_apf` | Vortex artificial potential fields — circulating flux around obstacles to avoid local minima. |
| `waypoint_follower_controller` | `examples.controllers.waypoint_follower_controller` | Pure pursuit / heading tracking to the current waypoint. |
| `simple_ackermann_controller` | `examples.controllers.simple_ackermann_controller` | Steering controller for Ackermann B-bots. |
| `PlannerController` | `examples.controllers.planner_controller` | Universal adapter that turns any [path planner](planners.md) into an engine controller, per robot type. |

### Using a controller

```python
from hivebr.engine import Simulator, load_config
from examples.controllers.potential_field import potential_field_controller

config = load_config("config/default.yaml")
sim = Simulator(config=config, controller=potential_field_controller)
sim.run()
```

### Writing one from scratch

```python
import numpy as np

def go_to_goal(robot, world, goal, config, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    dx, dy = goal[0] - robot.x, goal[1] - robot.y
    desired = np.arctan2(dy, dx)
    error = np.arctan2(np.sin(desired - robot.theta),
                       np.cos(desired - robot.theta))

    return {"v": min(0.6, np.hypot(dx, dy)), "omega": 2.0 * error}
```

## Per-robot dispatch in a fleet

When several B-bots share one controller, the engine calls the controller once
per B-bot, passing that B-bot, its own goal and its own LiDAR readings. This is
how [examples/multi_robot_differential.py](examples/multi_robot.md) reuses a
single Kanayama controller across the fleet.

For global, fleet-wide logic (optimization, task allocation), use
`SwarmController` instead — see the [OpenLab API](openlab_api.md).
