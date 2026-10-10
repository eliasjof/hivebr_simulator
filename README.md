# hivebr — OpenLab Simulator

A lightweight 2D simulation framework for single- and multi-robot (B-bot) mobile
navigation using **Pygame**, with a dual-paradigm OpenLab API for centralized and
decentralized control, sensors, external controllers, and interactive
visualization.

📖 **Documentation:** <https://eliasjof.github.io/hivebr_simulator/>

---

## Compile

```bash
python.exe -m build   

python.exe -m twine upload dist/*

sudo apt install python3-tk

```
Necessário colocar a API token obtida do site pipy.

---

## 🚀 Key Features

*   **Dual Environment Representation**: Supports both traditional coordinate-based circular obstacles AND image-based **Occupancy Grid Maps**.
*   **Interactive GUI**: 
    *   **Map Loading**: Load maps dynamically during simulation with custom resolution.
    *   **Theming**: Dynamic switching between Light and Dark themes.
    *   **Map Panning**: Drag the environment view using `SHIFT` + `Right Click`.
*   **Map Generation (Benchmarking)**: Built-in `MapGenerator` for 'U', 'L', and Random maze patterns.
*   **Precision Sensing**: Ray-casting based LiDAR using DDA algorithm for accurate grid-based collision.

---

## 🏗️ Architecture

- ✅ **Simulator (`nav_sim`)**: Handles physics, UI, sensors, and environment.
- ✅ **Occupancy Grid**: Automatic conversion of images to binary/inflated grids for collision and LiDAR.
- ✅ **External Controllers**: Easily pluggable navigation strategies.

---

## Supported Robot Models

- `holonomic`  
  Command:
  ```python
  {"vx": ..., "vy": ...}
  ```

- `differential`  
  Command:
  ```python
  {"v": ..., "omega": ...}
  ```

- `ackermann`  
  Command:
  ```python
  {"speed": ..., "steer": ...}
  ```

---

## 📡 Sensors

### LiDAR (2D)
The simulator provides a configurable 2D LiDAR:
- Angular scan
- Range-limited
- Returns `(angle, distance, hit_point)`

---

## ⚙️ Installation

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

pip install -r requirements.txt
```

---

## ▶️ Run Examples

```bash
python examples/run_holonomic.py
python examples/run_differential.py
python examples/run_maze.py
```

---

## 🗺️ Occupancy Grid Maps
You can define map sources directly in your config or load them dynamically:

```yaml
world:
  map_image: "maze.png"
  resolution: 0.1
  show_inflation: true
theme: "dark"
```

## ⌨️ User Interaction
- **Left Click**: Set Waypoint.
- **Right Click**: Add Obstacle (opens radius dialog).
- **SHIFT + Right Click**: Pan/Drag the environment.
- **Scroll**: Zoom.
- **UI Panel**: Toggle LiDAR, switch themes, load new maps.

---

## 🧩 Controller Interface

```python
def controller(robot, world, goal, config, dt, lidar_readings=None) -> dict:
    ...
```

---

## 🛑 Collision Handling
The simulator detects collisions using:
`d <= r_robot + r_obstacle`

- Immediate stop.
- Visual indicator (💥) displayed.

---

## 📄 License
Free for educational and research use.
