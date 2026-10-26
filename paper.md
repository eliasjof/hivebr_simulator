# hiveBr: An Open-Source 2D Multi-Robot Simulator for Navigation Research and Education

**Authors:** Elias J. R. Freitas  
**Affiliation:** Federal University of ABC (UFABC), Brazil  
**Repository:** https://github.com/eliasjof/hivebr_simulator  
**License:** MIT  

---

## Abstract

We present **hiveBr**, an open-source 2D simulation framework for single- and multi-robot mobile navigation research. The simulator provides a lightweight Pygame-based physics and rendering engine combined with a dual-paradigm OpenLab API that enables the same control logic to run in simulation and on physical robots. hiveBr supports seven kinematic models (differential, differential first-order, line follower, holonomic, hexagonal holonomic, Ackermann, and boat), high-fidelity LiDAR simulation with DDA ray-casting against occupancy grids and analytic circles, two environment representations (analytic obstacles and image-based occupancy grids with inflation), deterministic fleet stepping, pluggable path planners (A*, RRT, RRT*, PRM, BIT*, OMPL, RRT-Dubins), and a data logger for offline analysis. The simulator is designed for research reproducibility and educational use, with interactive GUI for rapid prototyping and a clean Python API for systematic experimentation.

---

## 1. Summary

**hiveBr** (hive Brazilian Robots) is a 2D multi-robot simulator written in Python, built on Pygame and NumPy, designed for mobile robot navigation research and education. The name follows the "hive" metaphor: each robot is called a **B-bot** (bee-bot), and a fleet is a **swarm**.

The simulator provides:

- **Seven kinematic models**: differential (unicycle), differential first-order (motor lag), line follower (TCRT5000 analog sensors), holonomic (omnidirectional), **hexagonal holonomic** (3 omni-wheels at 120°), Ackermann (car-like), and boat
- **Dual-paradigm OpenLab API**: decentralized agents (`HiveBrAgent`) or centralized controllers (`SwarmController`), with backend switching between simulation (`navsim2d`) and physical robots (ROS 2)
- **High-fidelity sensing**: LiDAR with DDA ray-casting against occupancy grids plus analytic circle intersection; line follower with 2/5/8 analog TCRT5000 sensors
- **Two environment representations**: analytic circular obstacles and image-based occupancy grids with configurable inflation
- **Deterministic fleet stepping**: frozen snapshot each timestep ensures results independent of robot update order
- **Path planning suite**: A*, RRT, RRT*, PRM, BIT*, OMPL integration, RRT-Dubins for non-holonomic robots
- **Data logging**: per-robot trajectory, command vs. actual velocities, collisions, lap timing (line follower), export to pickle/CSV
- **Interactive GUI**: pan/zoom, theme switching, waypoint/obstacle editing, track drawing for line follower, real-time parameter sliders

The simulator is installable via `pip install hivebr` and runs on Linux, Windows, and macOS.

---

## 2. Statement of Need

Mobile robotics research requires rapid iteration between algorithm design, simulation validation, and physical deployment. Existing tools present trade-offs:

| Tool | Strengths | Limitations |
|------|-----------|-------------|
| **Gazebo / ROS 2** | Industry standard, 3D, physics engines | Heavy, steep learning curve, slow iteration |
| **Webots** | Good physics, ROS bridge | Proprietary core, limited customization |
| **Stage** | Lightweight 2D, ROS integration | Dated codebase, limited kinematics |
| **Custom Python scripts** | Full control | No standardized API, no GUI, no logging |

**hiveBr** fills the gap for researchers and educators who need:

1. **Lightweight 2D simulation** with realistic kinematics and sensing, without 3D overhead
2. **Unified API** for both centralized and decentralized control paradigms
3. **Seamless sim-to-real transfer** via the OpenLab backend abstraction
4. **Reproducible experiments** with deterministic stepping and comprehensive logging
4. **Extensible architecture** for novel kinematics, sensors, and planners
5. **Educational accessibility** with interactive GUI and minimal dependencies

The hexagonal holonomic model (3 omni-wheels at 120°) addresses a specific need in omnidirectional robotics research, where most simulators only offer 4-wheel holonomic or generic omnidirectional models. The line follower model with analog TCRT5000 sensor simulation enables low-cost educational robotics research.

---

## 3. Statement of Field

Multi-robot systems (MRS) and swarm robotics are active research areas with applications in:

- **Search and rescue**: coordinated exploration of unknown environments
- **Environmental monitoring**: distributed sensing with aerial/ground robots
- **Logistics and warehouse automation**: fleet coordination and path planning
- **Precision agriculture**: multi-robot weed detection and treatment
- **Educational robotics**: low-cost platforms for teaching control and coordination

Simulation is essential for MRS research due to the cost and complexity of physical fleets. The field requires simulators that balance **physical fidelity** (kinematics, sensing, collisions) with **computational efficiency** (large fleets, long experiments) and **software engineering quality** (reproducibility, extensibility, CI/CD).

hiveBr contributes to this ecosystem by providing a **Python-first, 2D-focused simulator** that integrates with the scientific Python stack (NumPy, SciPy, Matplotlib) and the ROS 2 ecosystem via the OpenLab bridge.

---

## 4. Contribution

### 4.1 Hexagonal Holonomic Kinematics (Novel Model)

hiveBr implements a **3-wheel omnidirectional robot** with wheels at 60°, 180°, 300° (aligned with hexagon flat sides), matching commercial platforms like the **KUKA youBot** base and custom research robots.

**Forward kinematics** (wheel speeds → robot velocity):
$$\begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\theta} \end{bmatrix} = \mathbf{J}_f \begin{bmatrix} \omega_1 \\ \omega_2 \\ \omega_3 \end{bmatrix},\quad \mathbf{J}_f = \begin{bmatrix} -r\frac{\sqrt{3}}{2} & 0 & r\frac{\sqrt{3}}{2} \\[4pt] \frac{r}{2} & -r & \frac{r}{2} \\[4pt] \frac{r}{3L} & \frac{r}{3L} & \frac{r}{3L} \end{bmatrix}$$

**Inverse kinematics** (robot velocity → wheel speeds):
$$\begin{bmatrix} \omega_1 \\ \omega_2 \\ \omega_3 \end{bmatrix} = \mathbf{J}_f^{\dagger} \begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\theta} \end{bmatrix} = \begin{bmatrix} -\frac{2}{3r} & \frac{\sqrt{3}}{3r} & \frac{L}{r} \\[4pt] -\frac{2}{3r} & -\frac{\sqrt{3}}{3r} & \frac{L}{r} \\[4pt] \frac{4}{3r} & 0 & \frac{L}{r} \end{bmatrix} \begin{bmatrix} \dot{x} \\ \dot{y} \\ \dot{\theta} \end{bmatrix}$$

Where $r$ = wheel radius, $L$ = center-to-wheel distance. Three control modes: direct servo ($\omega_i$), world-frame ($v_x, v_y, \omega$), robot-frame ($v, \omega$).

### 4.2 Hexagonal Holonomic Line Follower (Novel Combination)

Combines the 3-wheel holonomic kinematics with **5-sensor TCRT5000 analog line array** for omnidirectional line following—a unique capability not found in other simulators. Enables research on:

- Omnidirectional line tracking with lateral drift correction
- PID control in robot frame with inverse kinematics
- Multi-robot line following with collision avoidance

### 4.3 Deterministic Fleet Stepping

Each timestep computes all robot commands from a **frozen snapshot** of fleet state (positions, velocities, sensor readings), then applies commands simultaneously. This eliminates update-order bias and ensures bitwise reproducibility given identical seeds.

### 4.4 Dual-Paradigm OpenLab API

| Paradigm | Class | Use Case |
|----------|-------|----------|
| **Decentralized** | `HiveBrAgent` | Swarm intelligence, consensus, formation control |
| **Centralized** | `SwarmController` | Trajectory optimization, global planning, MPC |

Same agent/controller code runs in simulation (`backend="navsim2d"`) or on physical robots (`backend="ros2"`) via ROS 2 bridge.

### 4.5 Comprehensive Sensor Suite

- **LiDAR**: Configurable rays (1–360), range, FOV; DDA ray-casting on occupancy grid + analytic circle intersection
- **Line follower**: 2/5/8 TCRT5000 sensors with adjustable aperture, noise, threshold; centroid error computation
- **Odometry**: Ground truth + optional Gaussian noise injection (`sigma_v`, `sigma_omega`)

### 4.6 Environment Representations

1. **Analytic obstacles**: Circular obstacles with exact collision detection and resolution policies (`stop`, `resolve`, `none`)
2. **Occupancy grids**: PNG/PGM maps with configurable resolution and inflation radius for planning
3. **Line maps**: Grayscale images for line follower (black line on white background)

### 4.7 Pluggable Planning and Logging

- **Planners**: A*, RRT, RRT*, PRM, BIT*, OMPL (via `ompl` Python bindings), RRT-Dubins
- **Logger**: Per-robot time series of pose, velocities (command vs. actual), collisions, lap times; export to pickle/CSV with collision sidecar

---

## 5. Software Design

### 5.1 Architecture Overview

```
hivebr/
├── engine/                 # Core simulation engine
│   ├── simulator.py        # Simulator class, main loop, event handling
│   ├── robots/             # Kinematic models (BaseRobot + 7 subclasses)
│   ├── world.py            # World, obstacles, occupancy grid, line map
│   ├── camera.py           # 2D camera with pan/zoom
│   ├── data_logger.py      # Logging and export
│   ├── planners/           # Path planners (A*, RRT*, etc.)
│   ├── ui/gui.py           # PyGame GUI with pygame_gui
│   └── interaction.py      # Collision detection and resolution
├── openlab/                # OpenLab API
│   ├── agent.py            # HiveBrAgent (decentralized)
│   ├── controller.py       # SwarmController (centralized)
│   └── backends/           # navsim2d, ros2
└── config.py               # Configuration loading (YAML + defaults)
```

### 5.2 Robot Class Hierarchy

```
BaseRobot (ABC)
├── DifferentialRobot           # v, ω commands
├── DifferentialRobotFirstOrder # + tau_v motor lag
├── LineFollowerRobot           # Differential + TCRT5000 sensors
├── HolonomicRobot              # vx, vy commands
├── HexagonalHolonomicRobot     # 3 omni-wheels, 3 control modes
├── HexagonalHolonomicLineFollower # 3-wheel + TCRT5000
├── AckermannRobot              # speed, steer (bicycle model)
└── BoatRobot                   # Differential kinematics, boat rendering
```

Each robot implements: `position`, `reset()`, `state()`, `step(command, dt)`, `draw(screen, camera)`.

### 5.3 Configuration System

- **YAML-based** with `load_config()` and `DEFAULT_CONFIG` fallback
- **Hierarchical**: `robot`, `world`, `lidar`, `noise`, `waypoints`, `gui`, `interaction`
- **GUI customization**: `gui.buttons` and `gui.sliders` lists control sidebar elements
- **Theme support**: `dark`/`light` palettes with runtime switching

### 5.4 Deterministic Execution

```python
def step_fleet(self, dt):
    # 1. Snapshot fleet state
    snapshot = [robot.state() for robot in self.robots]
    
    # 2. Compute commands from snapshot
    commands = [controller(robot, world, goal, config, dt, lidar) 
                for robot, goal, lidar in zip(self.robots, goals, lidar_readings)]
    
    # 3. Apply all commands
    for robot, cmd in zip(self.robots, commands):
        robot.step(cmd, dt)
```

### 5.5 Extensibility Points

| Extension | Method |
|-----------|--------|
| New robot | Subclass `BaseRobot`, register in `create_robot()` |
| New sensor | Add to robot `state()`, implement reading in `World` |
| New planner | Implement `plan(start, goal, world)` returning waypoints |
| New backend | Implement `OpenLabBackend` interface |
| New GUI element | Add to `config["gui"]["buttons/sliders"]` |

---

## 6. Practical Examples

### 6.1 Single Robot — Differential Drive with Kanayama Controller

```python
from hivebr.engine import Simulator, load_config

def kanayama_controller(robot, world, goal, cfg, dt, lidar):
    # Polar coordinate controller with orientation
    rho = np.linalg.norm([goal[0]-robot.x, goal[1]-robot.y])
    if rho < cfg["waypoints"]["goal_tolerance"]:
        return {"v": 0.0, "omega": 0.0}
    # ... control law ...
    return {"v": v, "omega": omega}

config = load_config("config/default.yaml")
sim = Simulator(config=config, controller=kanayama_controller)
sim.set_robot_waypoints(0, [[5, 7, 0.0], [8, 1, 0.0]])
sim.run()
```

### 6.2 Hexagonal Holonomic — Servo Control with Control Allocation

```python
from examples.run_hexagonal_holonomic import servo_controller

config = load_config("config/hexagonal_holonomic.yaml")
sim = Simulator(config=config, controller=servo_controller)
sim.run()

# servo_controller uses:
# 1. World-frame velocity for goal tracking
# 2. Inverse kinematics → wheel speeds
# 3. Control allocation: scale (vx, vy, ω) until |ω_i| ≤ servo_max_speed
```

### 6.3 Hexagonal Holonomic Line Follower — PID on Line Error

```python
from examples.run_hexagonal_holonomic_line_follower import line_follower_controller

config = load_config("config/hexagonal_holonomic_line_follower.yaml")
# Generates random track, places robot on tangent
sim = Simulator(config=config, controller=line_follower_controller)
sim.run()

# line_follower_controller:
# 1. robot.read_line_sensors(world.line_map) → robot.line_error ∈ [-1, 1]
# 2. PID on error → (v, ω) in robot frame
# 3. Inverse kinematics → (ω₁, ω₂, ω₃)
```

### 6.4 Multi-Robot Fleet — Decentralized Agents

```python
from hivebr import HiveBrAgent, SwarmExperiment

class FormationAgent(HiveBrAgent):
    def loop(self, state, neighbors):
        # Consensus-based formation keeping
        vx = sum(n.pose[0] for n in neighbors) / len(neighbors) - state.pose[0]
        vy = sum(n.pose[1] for n in neighbors) / len(neighbors) - state.pose[1]
        return vx, vy, 0.0

exp = SwarmExperiment(robots=5, backend="navsim2d")
exp.assign_agent(robot_ids=[0,1,2,3,4], agent_class=FormationAgent)
exp.run()
```

### 6.5 Centralized Swarm Controller

```python
from hivebr import SwarmController, SwarmExperiment

class MPCController(SwarmController):
    def compute_commands(self, fleet_state):
        # Centralized MPC for all robots
        commands = solve_mpc(fleet_state)
        return commands

exp = SwarmExperiment(robots=3, backend="navsim2d")
exp.assign_controller(MPCController())
exp.run()
```

### 6.6 Configuration-Driven GUI Customization

```yaml
gui:
  buttons:
    - start
    - reset
    - toggle_lidar
    - toggle_noise
    - toggle_theme
    - save_config
  sliders:
    - max_speed
    - max_omega
    - grid_size
    - noise_sigma
    - servo_max_speed   # Only shown for hexagonal_holonomic
```

---

## 7. Research Impact

### 7.1 Enabling Reproducible Multi-Robot Research

hiveBr's deterministic stepping, comprehensive logging, and configuration-driven experiments enable **bitwise reproducible** multi-robot studies. Researchers can:

- Archive full experiment configuration (YAML) + log (pickle) for exact reproduction
- Compare controllers across identical initial conditions and noise seeds
- Systematic parameter sweeps via config files or programmatic modification

### 7.2 Lowering Barrier for Omnidirectional Robotics

The hexagonal holonomic model with line follower combination enables research on **low-cost omnidirectional platforms** (3 omni-wheels + IR sensors) that are common in educational robotics (e.g., RoboCup Junior, FIRA) but unsupported in major simulators.

### 7.3 Sim-to-Real Transfer via OpenLab

The backend abstraction allows **zero-code-transfer** from simulation to physical B-bots:

```python
# Simulation
exp = SwarmExperiment(robots=3, backend="navsim2d")

# Physical deployment (same code)
exp = SwarmExperiment(robots=3, backend="ros2")
```

This accelerates the research cycle: develop in simulation → validate in sim → deploy to hardware without code changes.

### 7.4 Educational Impact

hiveBr is used in graduate robotics courses at UFABC for:

- **Mobile Robotics**: Kinematics, control, path planning labs
- **Multi-Robot Systems**: Consensus, formation, swarm behavior projects
- **Embedded Systems**: Line follower PID tuning on simulated and physical TCRT5000 arrays

The interactive GUI allows students to visualize concepts (kinematics, LiDAR, occupancy grids) without coding.

### 7.5 Publications and Citations

hiveBr has been used in:

- Freitas, E.J.R. et al. "Decentralized Formation Control with Hexagonal Holonomic Robots" (submitted)
- Undergraduate theses on line follower PID optimization
- Graduate projects on swarm exploration with occupancy grids

### 7.6 Community and Sustainability

- **Open source** (MIT license) on GitHub with issue tracker and PR workflow
- **CI/CD** with GitHub Actions (lint, type-check, test)
- **Documentation** with MkDocs Material + KaTeX math rendering
- **Extensible design** encourages community contributions of new robots, sensors, planners

---

## 8. Conclusion

hiveBr provides a **lightweight, extensible, and reproducible** 2D multi-robot simulator that bridges the gap between heavyweight 3D simulators and custom research scripts. Its novel contributions—the hexagonal holonomic kinematics, the holonomic line follower combination, deterministic fleet stepping, and the dual-paradigm OpenLab API—address specific needs in omnidirectional robotics, educational robotics, and sim-to-real transfer research.

By integrating with the scientific Python ecosystem and ROS 2, hiveBr enables researchers to focus on algorithm development rather than simulation infrastructure, while maintaining the physical fidelity required for meaningful validation.

---

## References

1. Kanayama, Y., Kimura, Y., Miyazaki, F., & Noguchi, T. (1990). "A stable tracking control method for an autonomous mobile robot." *IEEE ICRA*.
2. LaValle, S.M. (2006). *Planning Algorithms*. Cambridge University Press.
3. KUKA youBot Technical Specifications. KUKA Robotics.
4. RoboCup Junior Rules. RoboCup Federation.
5. ROS 2 Design Documentation. Open Robotics.

---

## Appendix: Installation and Quick Start

```bash
# Install
pip install hivebr

# Run differential drive example
python -m hivebr.examples.controle_robodiferencial

# Run hexagonal holonomic
python -m hivebr.examples.run_hexagonal_holonomic

# Run hexagonal holonomic line follower (generates track automatically)
python -m hivebr.examples.run_hexagonal_holonomic_line_follower --seed 42

# Run multi-robot fleet
python -m hivebr.examples.multi_robot
```

Full documentation: https://eliasjof.github.io/hivebr_simulator/