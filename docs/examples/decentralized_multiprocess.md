# Decentralized Swarm across CPU cores

Reference: [`examples/decentralized_multiprocess.py`](https://github.com/eliasjof/hivebr_simulator/blob/main/examples/decentralized_multiprocess.py)

A variant of the [Decentralized Swarm example](decentralized.md) where each
B-bot's controller runs on a **separate process**, so the fleet is spread over
several CPU cores.

## Why it works

The engine computes every B-bot's command from a *frozen snapshot* of the fleet
and only integrates the kinematics afterwards, so the per-agent control is
independent. Python's GIL blocks CPU parallelism with threads, so this example
maps the controllers over a `concurrent.futures.ProcessPoolExecutor`. The pygame
window stays in the main process; only the controller math runs in the workers.

## What it shows

- The engine seam `Simulator(..., fleet_controller=...)`.
- Building one **plain** task per B-bot and mapping it over a process pool.
- Passing only numbers (no engine objects) across process boundaries, so the
  tasks are picklable.
- A local Kanayama controller with a *directional* separation term.

## Key parts

The engine calls the controller once per frame:

```python
def parallel_fleet_controller(robots, goals, config, dt, lidar_readings=None):
    r_tol = float(config.get("waypoints", {}).get("goal_tolerance", 0.2))
    tasks = [...]                       # one plain tuple per B-bot
    commands = [{} for _ in robots]
    for index, v, w in pool.map(_worker, tasks):
        commands[index] = {"v": v, "omega": w}
    return commands
```

## Getting the waypoints right

Two details matter for the B-bots to reach **every** waypoint:

1. **Match the stop radius to the goal tolerance.** `compute_control` stops
   when `rho < r_tol`. This value must equal the engine's
   `waypoints.goal_tolerance` (0.1 in `config/default.yaml`); otherwise the
   B-bot parks just outside the tolerance circle and the waypoint never
   advances. The controller reads it straight from the engine `config`.
2. **Keep the routes clear of each other.** The separation term only brakes for
   neighbors that are *ahead* and adds a small steering bias, so crossing paths
   go around each other instead of stalling. Routes must still avoid two B-bots
   targeting the same point: they can never both sit inside the goal tolerance
   without overlapping, so they would deadlock.

## Run it

```bash
python examples/decentralized_multiprocess.py
python examples/decentralized_multiprocess.py --workers 4
```

The console prints the number of worker processes used. On Windows and macOS
the pool uses the `spawn` start method, so the script keeps its work under
`if __name__ == "__main__":` and hides the repeated pygame import banner with
`PYGAME_HIDE_SUPPORT_PROMPT`.

## Full source

```python title="examples/decentralized_multiprocess.py"
--8<-- "examples/decentralized_multiprocess.py"
```

See the [OpenLab API](../openlab_api.md) for the agent-centric
`HiveBrAgent.loop(state, neighbors)` alternative used by the single-process
decentralized example.
