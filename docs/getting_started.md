# Quick Start

This page runs a single B-bot through the low-level engine, which is exactly
what [examples/single_robot.md](examples/single_robot.md) does.

## 1. Configure the world

The engine is driven by a plain dictionary (usually loaded from YAML):

```python
from hivebr.engine import Simulator, load_config

config = load_config("config/default.yaml")
config["robot"]["type"] = "differential"
```

A minimal configuration looks like this:

```yaml
window:  { width: 1400, height: 750, panel_width: 300, title: "hivebr" }
world:   { width: 20.0, height: 12.0, grid_size: 1.0, obstacle_radius: 0.4 }
robot:   { type: differential, initial_pose: [2.5, 2.5, 0.0], radius: 0.2,
           max_speed: 3.0, max_omega: 4.0 }
lidar:   { enabled: false, num_rays: 101, range: 12.0, fov_deg: 360 }
theme:   dark
```

See [Configuration](configuration.md) for the full reference.

## 2. Write a controller

A controller is a callable that receives the B-bot, the world, the current goal,
the config, the timestep and the LiDAR readings, and returns a command dict.

```python
import numpy as np

def full_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    if goal is None:
        return {"v": 0.0, "omega": 0.0}

    xd, yd, theta_d = goal[0], goal[1], goal[2]
    dx, dy = xd - robot.x, yd - robot.y
    rho = np.hypot(dx, dy)
    if rho < 0.2:
        return {"v": 0.0, "omega": 0.0}

    alpha = np.arctan2(np.sin(np.arctan2(dy, dx) - robot.theta),
                       np.cos(np.arctan2(dy, dx) - robot.theta))
    beta = np.arctan2(np.sin(theta_d - robot.theta - alpha),
                      np.cos(theta_d - robot.theta - alpha))

    v = 0.35 * rho
    w = -1.0 * beta + 1.5 * alpha
    return {"v": v, "omega": w}
```

The command keys depend on the robot model — `v`/`omega` for differential,
`vx`/`vy` for holonomic, `speed`/`steer` for Ackermann. See
[Robot Models](robots.md).

## 3. Run

```python
sim = Simulator(config=config, controller=full_controller)
sim.set_using_orientation(True)
sim.set_goal_tolerance(0.2)
sim.set_robot_waypoints(0, [[5, 7, 0.0], [8, 1, 0.0]])
sim.run()
```

`set_robot_waypoints(index, points)` sets the route of B-bot `index`; for a
single robot the index is `0`.

## 4. Drive it from the GUI

Once the window is open:

- **Left click** adds a waypoint for the selected B-bot.
- **Right click** adds an obstacle (a radius dialog appears).
- **Middle drag** (or `Shift` + right drag) pans the view.
- **Mouse wheel** zooms.
- **Start / Pause** toggles the simulation, **Reset** restores initial poses.

Full list in [User Interface](user_interface.md).

!!! tip "Prefer the high-level API?"
    The same scenario can be expressed with `HiveBrAgent` and
    `SwarmExperiment`. See the [OpenLab API](openlab_api.md) and the
    [Decentralized Swarm example](examples/decentralized.md).
