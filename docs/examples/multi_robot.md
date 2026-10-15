# Multi-Robot Fleet (engine)

Reference: [`examples/multi_robot_differential.py`](https://github.com/eliasjof/hivebr_simulator/blob/main/examples/multi_robot_differential.py)

The multi-robot counterpart of the [single B-bot example](single_robot.md). A
single controller callable is called once per B-bot, each with its own goal and
LiDAR scan. The engine integrates all B-bots from a frozen snapshot.

## What it shows

- A `robots` list in the configuration (fleet definition).
- One route per B-bot via `set_robot_waypoints`.
- Per-robot fleet colors from the `fleet` palette.
- The robot-robot `interaction` policy (`collision_policy` + `robot_collision`).
- The LiDAR treating the other B-bots as moving obstacles (`lidar.enabled: true`).
- The multi-line HUD and `1`…`N` B-bot selection.

## Key parts

```python
config["robots"] = [
    {"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25},
    {"id": 1, "type": "differential", "initial_pose": [5.0, 5.0, 0.0], "radius": 0.25},
    {"id": 2, "type": "differential", "initial_pose": [18.0, 2.0, 0.0], "radius": 0.25},
    {"id": 3, "type": "differential", "initial_pose": [18.0, 10.0, 0.0], "radius": 0.25},
]
config["interaction"] = {
    "collision_policy": "stop",
    "robot_collision": True,
    "show_robot_links": True,
}
config["lidar"]["enabled"] = True   # other B-bots seen as moving obstacles

sim = Simulator(config=config, controller=full_controller)
for index, points in routes.items():
    sim.set_robot_waypoints(index, route_with_orientation(points))
sim.run()
```

## Run it

```bash
python examples/multi_robot_differential.py
```

## Full source

```python title="examples/multi_robot_differential.py"
--8<-- "examples/multi_robot_differential.py"
```

See [Multi-Robot Fleets](../multi_robot.md) for the interaction model and the
deterministic stepping guarantees.
