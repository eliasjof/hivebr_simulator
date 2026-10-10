# Single Robot — Differential Drive

Reference: [`examples/controle_robodiferencial.py`](https://github.com/eliasjof/hivebr_simulator/blob/main/examples/controle_robodiferencial.py)

A single differential B-bot driven by a **Kanayama (1990)** position-and-heading
controller in polar coordinates. This is the canonical low-level example: a
plain callable controller plus the interactive engine.

## What it shows

- The controller interface `(robot, world, goal, config, dt, lidar_readings)`.
- A `differential` B-bot with a battery model and a recharge routine.
- Setting a route directly on the waypoint manager.
- Orientation control and a goal tolerance.

## Key parts

```python
def full_controller(robot, world, goal, cfg, dt, lidar_readings=None, r_tol=0.2):
    ...
    rho   = np.linalg.norm([delta_x, delta_y])
    alpha = normalize_angle(np.arctan2(delta_y, delta_x) - theta)
    beta  = normalize_angle(theta_d - theta - alpha)
    ...
    return {"v": v, "omega": w}
```

The controller receives the current `goal` (a waypoint `[x, y, theta]`) for the
B-bot it is called with, so the same function can later be reused per robot in a
fleet.

## Run it

```bash
python examples/controle_robodiferencial.py
```

## Full source

```python title="examples/controle_robodiferencial.py"
--8<-- "examples/controle_robodiferencial.py"
```

Next: express the same behavior with the high-level API in the
[Decentralized Swarm example](decentralized.md), or scale to many B-bots in the
[Multi-Robot Fleet example](multi_robot.md).
