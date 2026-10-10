# OpenLab API

The `hivebr` package is a thin, backend-agnostic layer on top of the engine.
Its purpose: **write your robot logic once** and run it either in the local
simulator or on the physical arena, in a decentralized or centralized style.

The API never imports Pygame. All rendering lives in `hivebr.engine`.

## The dual paradigm

| | Decentralized (`HiveBrAgent`) | Centralized (`SwarmController`) |
| --- | --- | --- |
| Instances | One per B-bot (`N`) | Exactly one |
| You receive | Your `state` + `neighbors` | All `states` |
| Returns | A `Command` (or `(v, omega)`) | `{robot_id: Command}` |
| Great for | Local reactive control, obstacle avoidance, distributed consensus | Global planning, optimization (DE, L-SHADE), task allocation |
| Physical backend | One ROS 2 node per agent | One node publishing per-robot commands |

Mono-robot is simply `N = 1`, with no API change.

## States and commands

```python
from hivebr import RobotState, Command, FleetState
```

- **`Command(v, omega)`** — a velocity command.
- **`RobotState`** — an immutable snapshot: `id`, `x`, `y`, `theta`, `v`,
  `omega`, `type`, `radius`, `battery`, and `goal` (the current waypoint
  `(x, y)` or `(x, y, theta)`, or `None`).
- **`FleetState`** — `t` plus `{robot_id: RobotState}`.

## Decentralized example

```python
from hivebr import HiveBrAgent, SwarmExperiment

class Patrol(HiveBrAgent):
    def setup(self):
        self.speed = self.params.get("speed", 0.5)

    def loop(self, state, neighbors):
        if state.goal is None:
            return (0.0, 0.0)
        dx = state.goal[0] - state.x
        dy = state.goal[1] - state.y
        theta = state.goal[2] if len(state.goal) > 2 else state.theta
        # ... compute (v, omega) using state and neighbors ...
        return v, omega

exp = SwarmExperiment(robots=3, backend="navsim2d")
exp.assign_agent(robot_ids=[0, 1, 2], agent_class=Patrol, speed=0.6)
exp.assign_route(0, [[5, 2, 0.0], [5, 6, 0.0]])
exp.run()
```

- `HiveBrAgent.setup()` runs once when the experiment builds its agents.
- `loop(state, neighbors)` runs every timestep. `neighbors` is
  `{robot_id: RobotState}` filtered by the communication radius.
- Return a `Command`, a `(v, omega)` tuple, or a `{"v": …, "omega": …}` dict.

## Centralized example

```python
from hivebr import SwarmController, SwarmExperiment

class GlobalPlanner(SwarmController):
    def loop(self, states):
        return {rid: (0.0, 0.0) for rid in states}

exp = SwarmExperiment(robots=4, backend="navsim2d")
exp.set_controller(GlobalPlanner())
exp.run()
```

The single controller receives `states = {robot_id: RobotState}` and returns one
command per B-bot, so it can run global optimization over the whole fleet.

## `SwarmExperiment`

| Member | Purpose |
| ------ | ------- |
| `SwarmExperiment(robots, backend, config, dt, orientation, goal_tolerance, comm_radius)` | Create an experiment. `robots` is an int or a list of specs. |
| `assign_agent(robot_id=…, robot_ids=[…], agent_class=…, **params)` | Bind a `HiveBrAgent` (heterogeneous fleets are supported). |
| `set_controller(controller)` | Bind a `SwarmController` (centralized mode). |
| `assign_route(robot_id, waypoints)` | Give a B-bot its route. |
| `run()` | Build and run on the selected backend. |
| `reset()` / `close()` | Reset agents and backend / tear down. |

`orientation` and `goal_tolerance` are injected into the engine config, and
`comm_radius` controls neighbor visibility (defaulting to
`config["interaction"]["comm_radius"]`).

## How the goal reaches the agent

The engine's per-robot waypoint manager supplies the current goal; the bridge
copies it into `RobotState.goal` together with the pose and velocities. Your
agent simply reads `state.goal`.

## Backends

| `backend` | Status | Description |
| --------- | ------ | ----------- |
| `"navsim2d"` | Available | Local Pygame simulation via `hivebr.engine`. |
| `"ros2"` | Stub | Physical arena: one ROS 2 node per agent, or one node for a controller. |

Because `HiveBrAgent`/`SwarmController` depend only on `RobotState`/`Command`,
the ROS 2 backend can reuse the exact same user code. See the
[Bridge & Backends reference](api/bridge.md).

## API reference

- [`HiveBrAgent`, `SwarmController`, `SwarmExperiment`](api/core.md)
- [`RobotState`, `Command`, `FleetState`](api/state.md)
- [Kinematics helpers](api/kinematics.md)
- [Bridge & backends](api/bridge.md)
