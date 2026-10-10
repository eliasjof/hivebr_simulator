# Multi-Robot Fleets

hivebr is multi-robot by construction: every B-bot has its own pose, path,
waypoint route, LiDAR scan and collision flag. A mono-robot run is just a fleet
with `N = 1`.

## Declaring a fleet

Add a `robots` list to the configuration. Each entry overrides the base `robot`
block and may carry a render `color`.

```yaml
robots:
  - { id: 0, type: differential, initial_pose: [2.0, 2.0, 0.0], radius: 0.25 }
  - { id: 1, type: differential, initial_pose: [5.0, 5.0, 0.0], radius: 0.25 }
  - { id: 2, type: ackermann,    initial_pose: [18.0, 2.0, 0.0] }
```

If `robots` is omitted, the engine builds one B-bot from `robot`.

## What the engine exposes

| Attribute | Description |
| --------- | ----------- |
| `sim.robots` | List of `BaseRobot`. |
| `sim.num_robots` | Fleet size. |
| `sim.waypoint_managers` | One route per B-bot. |
| `sim.robot_lidar_readings` | One scan per B-bot. |
| `sim.collisions` | One collision flag per B-bot. |
| `sim.selected_robot_index` | B-bot currently targeted by the GUI. |
| `sim.robot`, `sim.waypoints`, `sim.lidar_readings`, `sim.collision` | Convenience aliases for the **selected** B-bot. |

### Helpers

```python
sim.set_robot_waypoints(1, [[10, 5, 0.0], [10, 9, 0.0]])   # route for B-bot 1
sim.robot_goal(1)                                          # current waypoint
sim.select_robot(1)                                        # programmatic selection
sim.go_to_recharge_place(id=0, robot_index=2)
```

## Deterministic, order-independent stepping

Each timestep the engine:

1. updates waypoints and LiDAR for every B-bot,
2. computes **all** commands from a *frozen snapshot* of the fleet,
3. integrates every B-bot simultaneously,
4. checks static collisions per B-bot,
5. resolves robot-robot interaction.

Because commands are computed before any B-bot moves, the result does not depend
on update order — matching how decentralized agents act on the last received
state.

## Robot-robot interaction

Configure it under `interaction`:

```yaml
interaction:
  collision_policy: stop     # "stop" | "resolve" | "none"
  robot_safety_margin: 0.0
  resolve_push: 0.05
  comm_radius: null
  show_robot_links: false
```

| `collision_policy` | Behavior |
| ------------------ | -------- |
| `stop` | Both B-bots of an overlapping pair are flagged and frozen until **Reset**. |
| `resolve` | Overlaps are relaxed by nudging the pair apart along the normal (`resolve_push`, capped per step). |
| `none` | Overlaps are detected/flagged but B-bots keep moving (useful for soft-cost experiments). |

The detection test is `distance < r_i + r_j + robot_safety_margin`.

### Communication topology

`comm_radius` defines visibility for decentralized agents:

- `null` → full visibility (every B-bot sees every other).
- a number → only B-bots within that radius are considered neighbors.

Set `show_robot_links: true` to draw the resulting communication graph. The same
`comm_radius` is honored by the [OpenLab API](openlab_api.md) when building the
neighbor list passed to each `HiveBrAgent`.

## Per-robot controllers

A single callable controller is invoked once per B-bot with that B-bot's own
goal and scan:

```python
sim = Simulator(config=config, controller=full_controller)
```

For fleet-wide logic, pass a `fleet_controller` instead:

```python
def fleet_controller(robots, goals, config, dt, lidar_readings):
    # return a list (or {index: command}) with one command per B-bot
    return [{"v": 0.3, "omega": 0.0} for _ in robots]

sim = Simulator(config=config, fleet_controller=fleet_controller)
```

This is the seam the OpenLab API uses to plug in `SwarmController`.

## Interactive fleet control

Press `1`…`9` to select a B-bot; waypoint clicks then target the selected one.
The HUD lists every B-bot with its color and collision status. See the
[Multi-Robot Fleet example](examples/multi_robot.md).
