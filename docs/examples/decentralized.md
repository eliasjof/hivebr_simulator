# Decentralized Swarm (OpenLab API)

Reference: [`examples/decentralized_swarm.py`](https://github.com/eliasjof/hivebr_simulator/blob/main/examples/decentralized_swarm.py)

A heterogeneous fleet of `HiveBrAgent`s. Each B-bot runs its own instance of the
same agent class (with per-robot parameters), sees only its own state plus its
neighbors, and reads its waypoint from `state.goal`.

## What it shows

- The decentralized paradigm: `HiveBrAgent.loop(state, neighbors)`.
- `SwarmExperiment.assign_agent` for homogeneous and heterogeneous fleets.
- `SwarmExperiment.assign_route` to give each B-bot its route.
- A local separation term computed from the visible neighbors.
- Communication radius (`comm_radius`) shaping who sees whom.
- The backend seam: change `backend="ros2"` to target the physical arena.

## Key parts

```python
class PatrolAgent(HiveBrAgent):
    def setup(self):
        self.kp = self.params.get("kp", 0.35)
        self.sep_gain = self.params.get("sep_gain", 0.0)

    def loop(self, state, neighbors):
        goal = state.goal
        if goal is None:
            return (0.0, 0.0)
        # Kanayama control using state.x, state.y, state.theta, goal
        # plus a reactive separation term over `neighbors`
        return (v, w)
```

```python
exp = SwarmExperiment(robots=fleet, backend="navsim2d", config=config,
                      orientation=True, goal_tolerance=0.2)
exp.assign_agent(robot_id=0, agent_class=PatrolAgent, sep_gain=0.5, kp=0.45)
exp.assign_agent(robot_ids=[1, 2, 3], agent_class=PatrolAgent, sep_gain=0.9)
exp.assign_route(0, route_with_orientation([(2, 2), (5, 2), (5, 6), (2, 6)]))
exp.run()
```

## Run it

```bash
python examples/decentralized_swarm.py
```

Press `1`…`4` to select a B-bot; the HUD shows each agent's color and collision
state.

## Full source

```python title="examples/decentralized_swarm.py"
--8<-- "examples/decentralized_swarm.py"
```

See the [OpenLab API](../openlab_api.md) for the full `SwarmExperiment` surface.
