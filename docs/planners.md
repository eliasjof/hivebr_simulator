# Path Planners

Planners compute a geometric path from a start pose to a goal. They live in
`examples/planners` and share the `BasePlanner` interface.

## `BasePlanner`

```python
class BasePlanner(ABC):
    def __init__(self, bounds, robot_radius=0.3, seed=None): ...
    def plan(self, start, goal, obstacles, occupancy_map=None) -> (path, DebugData): ...
    @abstractmethod
    def _plan(self, start, goal, obs_list, occupancy_map=None): ...
```

- `bounds` is `(xmin, xmax, ymin, ymax)` in metres.
- `obstacles` is `world.obstacles` (the engine's `[x, y, r]` arrays).
- `occupancy_map` is an optional `OccupancyGridMap`.
- `plan` returns a list of `(x, y)` from start to goal (or `None`) **and** a
  `DebugData` object describing the search tree/roadmap for visualization.

Subclasses only implement `_plan`. Shared collision helpers
(`_point_free`, `_segment_free`, `_in_bounds`, `_random_sample`, `_steer`, …)
are provided by the base class.

## Available planners

| Planner | Import | Class / type |
| ------- | ------ | ------------ |
| A* | `examples.planners.astar` | `AStarPlanner` — grid-based A* on an inflated occupancy grid. |
| RRT | `examples.planners.planners` | `RRTPlanner` — rapidly-exploring random tree. |
| RRT* | `examples.planners.planners` | `RRTStarPlanner` — asymptotically optimal RRT. |
| PRM | `examples.planners.planners` | `PRMPlanner` — probabilistic roadmap. |
| BIT* | `examples.planners.planners` | `BITStarPlanner` — batch informed trees. |
| OMPL | `examples.planners.ompl_planner` | `OMPLPlanner` / `OMPLPlannerAdapter` — wraps an OMPL planner (`RRT`, `RRTConnect`, `PRM`, `BIT*`, …). Requires `ompl`. |
| RRT-Dubins | `examples.planners.rrtdubins` | Dubins-path variants for car-like (Ackermann) B-bots. |

## Connecting a planner to the engine

`PlannerController` turns any planner into an engine controller and draws the
path plus debug structure on screen.

```python
from examples.planners.planners import RRTStarPlanner
from examples.controllers.planner_controller import PlannerController
from hivebr.engine import Simulator, load_config

config = load_config("config/default.yaml")
bounds = (0, config["world"]["width"], 0, config["world"]["height"])

planner = RRTStarPlanner(bounds, robot_radius=config["robot"]["radius"], seed=1)
controller = PlannerController(planner)

sim = Simulator(config=config, controller=controller.controller,
                draw_callback=controller.draw_callback)
sim.run()
```

## Writing your own planner

```python
from examples.planners.base_planner import BasePlanner, DebugData

class StraightPlanner(BasePlanner):
    def _plan(self, start, goal, obs_list, occupancy_map=None):
        path = [start, goal]
        return path, DebugData()
```

See also the [Controllers](controllers.md) page for alternative (reactive)
navigation strategies.
