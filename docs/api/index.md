# API Reference

This reference is generated automatically from the source code and its
**docstrings** using [mkdocstrings](https://mkdocstrings.github.io/). Every page
below corresponds to a Python module of the `hivebr` package.

- **OpenLab API** — the backend-agnostic layer you program against:
  `HiveBrAgent`, `SwarmController`, `SwarmExperiment`, states and commands, and
  the backend bridge.
- **Engine** — the Pygame physics/renderer: simulator, robots, world, sensors,
  occupancy grids, waypoints, camera, logging and map generation.

```python
# Locations used by the reference pages
hivebr.core          # HiveBrAgent, SwarmController, SwarmExperiment
hivebr.state         # Command, RobotState, FleetState
hivebr.kinematics    # clamp, wrap_to_pi, wheel_speeds, apply_limits
hivebr.bridge        # Backend, NavSim2DBackend, Ros2Backend, create_backend
hivebr.engine        # Simulator, load_config, create_fleet, interaction
```

Use the sidebar to browse. Because this page set is generated from docstrings,
improving a docstring in the source immediately improves the documentation.
