# Data Logging & Analysis

The engine records the whole fleet every frame while the simulation is running.
Each B-bot gets its own time series of pose, **commanded** velocity and
**actual** velocity, plus a per-frame `collision` flag. Every collision event
(robot–robot, robot–obstacle or robot–grid) is stored separately with its
timestamp.

The recorder is `sim.logger`, an instance of
[`DataLogger`](api/data_logger.md) created automatically by the `Simulator`.

## What gets recorded

| Signal | Where | Notes |
| ------ | ----- | ----- |
| `t, x, y, theta` | every frame | Pose sampled from `robot.state()`. |
| command | every frame | Raw controller output (before noise/saturation). |
| real | every frame | Velocity actually executed (after saturation/kinematics). |
| `collision` | every frame | `1` if that B-bot is flagged in collision, else `0`. |
| `segment` | every frame | New segment whenever new waypoints are added. |
| collision events | `MultiRobotLog.collision_events` | `{t, kind, robots, ...}`. |

Command vs. real is exactly what the plot window exposes as separate signals
(see [Plotting](#plotting-the-log)).

## Saving and exporting the log

### From the GUI

| Button | Effect |
| ------ | ------ |
| **Export Log** | Saves the whole fleet to `.pkl` (pickle) or `.csv`, chosen by the dialog's extension. |
| **Plot Log** | Opens the interactive plot window. |
| **Reset Logger** | Discards the recorded log. |

### Programmatically (single Simulator)

```python
sim.run()                         # run the experiment

sim.logger.save("run_01.pkl")     # full log (pickle, recommended)
sim.logger.save_csv("run_01.csv") # per-frame CSV (+ *_collisions.csv)
sim.logger.export("run_02.csv")   # picks pickle/CSV by extension
sim.logger.print_collisions()     # human-readable collision summary
sim.logger.plot()                 # open the interactive plot window
```

Loading a previously saved run:

```python
from hivebr.engine import DataLogger

log = DataLogger.load("run_01.pkl")   # -> MultiRobotLog
print(log.collision_events)
log.plot_log()
```

### Programmatically (decentralized `SwarmExperiment`)

In decentralized mode the `DataLogger` lives inside the engine's `Simulator`,
which is created by the `navsim2d` backend. The experiment exposes it after
`run()`:

```python
exp = SwarmExperiment(robots=fleet, backend="navsim2d", config=config)
exp.assign_agent(robot_ids=[0, 1, 2], agent_class=PatrolAgent)
exp.run()

exp.save_log("swarm.pkl")     # .pkl or .csv by extension
exp.print_collisions()        # collisions of the whole experiment
exp.plot_log()                # interactive plot window
# or access the engine directly: exp.simulator.logger
```

## Example of a saved log

`save_csv("run.csv")` writes one row per B-bot per frame, and a companion
`run_collisions.csv` with one row per collision event.

=== "run.csv (per-frame)"

    ```text
    robot,robot_type,segment,t,x,y,theta,collision,v,omega,v_real,omega_real,wp_index
    0,differential,-1,0.03,2.009,2.0,0.0,1,0.3,0.0,0.3,0.0,0
    0,differential,-1,0.06,2.009,2.0,0.0,1,0.3,0.0,0.3,0.0,0
    0,differential,-1,0.09,2.009,2.0,0.0,1,0.3,0.0,0.3,0.0,0
    0,differential,-1,0.12,2.009,2.0,0.0,1,0.3,0.0,0.3,0.0,0
    ```

=== "run_collisions.csv (events)"

    ```text
    t,kind,robot_a,robot_b,obstacle_index,obstacle_x,obstacle_y,distance,description
    0.03,robot,0,1,,,,0.0,[    0.03s] COLISÃO robô-robô: B-Bot0 <-> B-Bot1 (d=0.000 m)
    ```

The pickle (`.pkl`) keeps the richer object graph and is the format to reload
with `DataLogger.load`:

```python
MultiRobotLog(
    logs=OrderedDict([
        (0, SimLog(robot_type="differential", robot_index=0, label="B-Bot0",
                   frames=[Frame(t=0.03, x=2.009, y=2.0, theta=0.0,
                                 v=0.3, omega=0.0, v_real=0.3, omega_real=0.0,
                                 collision=True, segment=-1), ...])),
        (1, SimLog(...)),
    ]),
    collision_events=[
        {"t": 0.03, "kind": "robot", "robots": [0, 1], "distance": 0.0},
    ],
)
```

Each collision event carries:

| Field | Meaning |
| ----- | ------- |
| `t` | Simulation time (s) at the rising edge of the collision. |
| `kind` | `robot`, `obstacle` or `grid`. |
| `robots` | The B-bot(s) involved (`[i]` or `[i, j]`). |
| `obstacle_index` / `obstacle_xy` | Obstacle involved (when `kind == "obstacle"`). |
| `distance` | Surface distance for robot–robot pairs. |

`DataLogger.print_collisions()` renders the same information:

```text
[DataLogger] 2 colisão(ões) registrada(s):
  [    0.03s] COLISÃO robô-robô: B-Bot0 <-> B-Bot1 (d=0.000 m)
  [    1.20s] COLISÃO B-Bot2 com obstáculo #0 em (6.00, 5.00)
```

## Plotting the log

The interactive plot window (Tk + Matplotlib) lets you pick B-bots, signals,
the subplot grid and whether to overlay B-bots. Velocity signals are available
both **combined** (command vs. actual overlaid on a single axis) and **split**:

| Signal | Content |
| ------ | ------- |
| Linear velocity (command vs actual) | Both linear curves on one axis (solid = command, dashed = actual). |
| Linear velocity (command) | Linear command only. |
| Linear velocity (actual) | Linear actual only. |
| Angular velocity (command vs actual) | Both angular curves on one axis. |
| Angular velocity (command) | Angular command only. |
| Angular velocity (actual) | Angular actual only. |

This makes it easy to see how much of the command the robot actually executed
(saturation, first-order lag, collisions, ...).

See the [Data Logging API reference](api/data_logger.md) for the full surface.
