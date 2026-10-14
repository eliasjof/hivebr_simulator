<p align="center">
  <img src="https://raw.githubusercontent.com/eliasjof/hivebr_simulator/main/hivebr-bar.png" alt="hiveBr — Brazilian Open Lab for Multi-Robots" width="100%">
</p>

# 🐝hiveBr — OpenLab Simulator

[![PyPI version](https://img.shields.io/pypi/v/hivebr.svg)](https://pypi.org/project/hivebr/)
[![Python versions](https://img.shields.io/pypi/pyversions/hivebr.svg)](https://pypi.org/project/hivebr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/eliasjof/hivebr_simulator/blob/main/LICENSE)
[![Docs](https://img.shields.io/badge/docs-online-blue.svg)](https://eliasjof.github.io/hivebr_simulator/)



A lightweight 2D simulation framework for **single- and multi-robot mobile
navigation**, built on Pygame, with a dual-paradigm **OpenLab API** for
centralized and decentralized control.

Robots in the simulator are called **B-bots** (for *bee*), keeping the hive
metaphor.

📖 **Full documentation:** <https://eliasjof.github.io/hivebr_simulator/>

---

## Installation

```bash
pip install hivebr
```

Optional extras:

```bash
pip install "hivebr[maps]"   # occupancy grids (Pillow + scipy)
pip install "hivebr[plot]"   # data logger plots (matplotlib)
```

## Quick start

```python
from hivebr import HiveBrAgent, SwarmExperiment

class Patrol(HiveBrAgent):
    def loop(self, state, neighbors):
        # state.goal holds the current waypoint (x, y, theta)
        return 0.5, 0.0

exp = SwarmExperiment(robots=3, backend="navsim2d")
exp.assign_agent(robot_ids=[0, 1, 2], agent_class=Patrol)
exp.assign_route(0, [[5, 2, 0.0], [5, 6, 0.0]])
exp.run()
```

A single robot is just a fleet with `N = 1`. Switching `backend="ros2"` reuses
the same agent code on the physical arena.

## Dual paradigm

| Decentralized — `HiveBrAgent` | Centralized — `SwarmController` |
| ----------------------------- | ------------------------------- |
| One instance per B-bot | Exactly one instance |
| Receives its `state` + `neighbors` | Receives all `states` |
| Returns a command | Returns `{robot_id: command}` |
| Reactive control, consensus | Global planning, optimization (DE, L-SHADE) |

## Features

- **Mono or fleet, one API.** A single robot is a fleet with `N = 1`.
- **Interactive GUI.** Pan/zoom, load occupancy-grid maps, switch themes,
  toggle LiDAR, add waypoints and obstacles with the mouse.
- **Two environment representations.** Analytic circular obstacles *and*
  image-based occupancy grids with inflation.
- **Precision sensing.** Ray-casting LiDAR (DDA) against the grid plus analytic
  circle intersections.
- **Deterministic fleets.** Each timestep is computed from a frozen snapshot of
  the fleet state, independent of update order.
- **Research-ready.** Pluggable controllers, path planners (A*, RRT, RRT*, PRM,
  BIT*, OMPL, RRT-Dubins), and a data logger for offline analysis.

## Robot models

| `type` | Command |
| ------ | ------- |
| `differential` | `{"v": ..., "omega": ...}` |
| `differential_firstorder` | `{"v": ..., "omega": ...}` |
| `holonomic` | `{"vx": ..., "vy": ...}` |
| `ackermann` | `{"speed": ..., "steer": ...}` |
| `boat` | `{"v": ..., "omega": ...}` |

## Run the examples

```bash
# from a clone of the repository (examples are not shipped in the wheel)
python examples/controle_robodiferencial.py
python examples/decentralized_swarm.py
python examples/multi_robot_differential.py
python examples/multi_line_follower.py
```

## Links

- Documentation: <https://eliasjof.github.io/hivebr_simulator/>
- Repository: <https://github.com/eliasjof/hivebr_simulator>
- Issue tracker: <https://github.com/eliasjof/hivebr_simulator/issues>

## License

MIT — free for educational and research use. See [LICENSE](LICENSE).

<p align="center">
  <img src="https://raw.githubusercontent.com/eliasjof/hivebr_simulator/main/hivebr-logo.png" alt="hivebr logo" width="180">
</p>
