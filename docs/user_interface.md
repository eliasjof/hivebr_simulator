# User Interface

The engine opens a resizable Pygame window split into a **world view** (left)
and a **control panel** (right).

## Mouse and keyboard

| Input | Action |
| ----- | ------ |
| **Left click** (world) | Add a waypoint for the selected B-bot. If `waypoints.define_orientation` is on, a dialog asks for the final heading. |
| **Left drag** (draw mode) | Draw the line-follower track (while **Draw Track** is active). |
| **Right click** (world) | Add a circular obstacle; a dialog asks for its radius. |
| **Middle drag** | Pan the camera. |
| **`Shift` + right drag** | Pan the camera (alternative). |
| **Mouse wheel** | Zoom in/out around the cursor. |
| **`1` … `9`** | Select B-bot 0 … 8. The selected B-bot is highlighted in the HUD. |

## Control panel buttons

| Button | Effect |
| ------ | ------ |
| **Start / Pause** | Toggle the simulation loop. |
| **Reset** | Restore every B-bot to its initial pose and clear collisions. |
| **Clear Path** | Erase the traced path of every B-bot. |
| **Clear Waypoints** | Remove the routes of all B-bots. |
| **Clear Obstacles** | Remove all circular obstacles. |
| **Load Map** | Load an occupancy-grid image; a dialog asks for the resolution in `m/pixel`. |
| **Draw Track** | Toggle the line-follower track editor. While on, the simulation pauses and left-drag paints the black line on a white canvas. |
| **Apply Track** | Convert the drawing into a `LineTrackMap`, install it in the world, save it to `world.drawn_line_map_image`, and place the B-bot at the start of the stroke (aligned with its tangent). |
| **Clear Track** | Erase the drawing canvas. |
| **Toggle LiDAR** | Enable/disable LiDAR rendering. |
| **Toggle Noise** | Enable/disable the Gaussian velocity noise (`noise` config section). |
| **Toggle Theme** | Switch between the `dark` and `light` palettes. |
| **Save Config** | Write the current world, obstacles and waypoints to `config/default.yaml`. |
| **Center Camera** | Recenter the view on the world origin. |
| **Plot Log** | Open the interactive plot window (Tk + Matplotlib) to inspect every B-bot: pick robots, signals (trajectory, position/orientation error, linear/angular velocity cmd vs real, ...), the subplot grid, and save the figure. |
| **Export Log** | Save the recorded log of the whole fleet to `.pkl` (pickle) or `.csv`. |
| **Reset Logger** | Discard the recorded log. |

## Sliders

| Slider | Applies to |
| ------ | ---------- |
| **Max Speed** | `max_speed` of the whole fleet. |
| **Max Omega** | `max_omega` of differential B-bots. |
| **Max Steering** | `max_steer` of Ackermann B-bots. |
| **Grid Size** | World grid spacing. |
| **Noise Sigma** | Gaussian velocity noise magnitude; moving it above 0 enables the noise and updates `sigma_v`/`sigma_omega`. |

## HUD

The heads-up display shows:

- A **header** with run state, fleet size, selected B-bot, FPS, obstacle count
  and zoom.
- A **detail line** for the selected B-bot: type, pose, motion command, waypoint
  progress, distance to the goal and a `[COLLISION]` marker.
- One **compact line per B-bot**, color-coded with its fleet color. A leading
  `*` marks a B-bot in collision.

## Collision indicator

When a B-bot is in collision, an explosion sprite is drawn at its position and
its HUD line is flagged. With the `stop` interaction policy the B-bot freezes
until **Reset**. See [Multi-Robot Fleets](multi_robot.md) for pairing policies.
