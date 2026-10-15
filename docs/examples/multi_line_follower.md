# Multi Line Follower (same track, same start)

Reference: [`examples/multi_line_follower.py`](https://github.com/eliasjof/hivebr_simulator/blob/main/examples/multi_line_follower.py)

Several `line_follower` B-bots share **one track** and start from the **same
point**, each with a different PID gain set. Under identical conditions you can
compare how the tuning affects lap times and stability.

## What it shows

- A fleet of `line_follower` B-bots with the same initial pose.
- Per-B-bot gains attached as `robot.pid_params`.
- Disabling the robot-robot collision so the overlapped B-bots do not stop each
  other (`collision_policy: none`, `robot_collision: false`).
- The per-B-bot timing in the HUD (`show_times`, **Toggle Times**).
- A per-B-bot result table printed when the window closes.

## Key parts

```python
# Same start point for every B-bot
config["robots"] = [
    {"id": i, "type": "line_follower",
     "initial_pose": [x0, y0, theta0], "radius": 0.05}
    for i in range(num_robots)
]

# Do not evaluate robot-robot collisions (they start overlapped)
config["interaction"] = {"collision_policy": "none", "robot_collision": False}
config["show_times"] = True

sim = Simulator(config=config, controller=line_pid_controller)
for i, robot in enumerate(sim.robots):
    robot.pid_params = GAIN_SETS[i]      # per-B-bot PID gains
sim.run()
```

The controller reads the gains from the B-bot it is called with:

```python
def line_pid_controller(robot, world, goal, cfg, dt, lidar_readings=None):
    robot.read_line_sensors(world.line_map)
    pid = getattr(robot, "pid_params", None) or cfg.get("line_pid", {})
    # error = robot.line_error ; omega = kp*error + ki*∫error + kd*d(error)
    return {"v": v, "omega": omega}
```

## Run it

```bash
python examples/multi_line_follower.py --robots 4 --spread 0.0
```

Useful flags: `--seed`, `--sensors` (2/5/8), `--robots`, `--spread`
(lateral offset; `0` = exactly the same point), `--regenerate`.

## Saving the comparison

The run is recorded by the shared [data logger](../logging.md). After closing
the window:

```python
sim.logger.save("multi_line_follower.pkl")
for i, robot in enumerate(sim.robots):
    print(f"B-Bot{i}: {robot.lap_statistics()}")
```

## Full source

```python title="examples/multi_line_follower.py"
--8<-- "examples/multi_line_follower.py"
```

See [Robot Models](../robots.md#line-follower-tcrt5000) for the line-follower
configuration and [Multi-Robot Fleets](../multi_robot.md) for the collision flag.
