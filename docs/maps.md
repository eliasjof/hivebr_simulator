# Maps & Occupancy Grids

`hivebr` supports two environment representations at the same time:

1. **Analytic circular obstacles** (`world.obstacles`) — fast, good for
   prototyping and for adding obstacles interactively.
2. **Image-based occupancy grids** (`world.grid_map`) — pixel maps converted to
   binary/inflated grids for collision and LiDAR.

## Occupancy grids

Point the config to an image and give the resolution in metres per pixel:

```yaml
world:
  map_image: "maze.png"
  resolution: 0.1
  show_inflation: true
```

Dark pixels (`< 128`) are treated as occupied. The grid is **inflated** by the
robot radius (plus a 5 cm safety margin) so a point robot never cuts corners.

### Loading a map at runtime

```python
sim.world.load_map("path/to/map.png", resolution=0.1)
sim.grid_map = sim.world.grid_map
```

The **Load Map** button in the GUI does the same and asks for the resolution.

### Building a grid programmatically

```python
from hivebr.engine import Simulator

grid = my_boolean_array                  # True = occupied
sim.set_map_from_grid(grid, resolution=0.1, name="generated_map.png")
```

### Collision and ray casting

```python
occupied = sim.world.grid_map.is_occupied(x, y, use_inflated=True)
distance, hit = sim.world.grid_map.cast_ray(x, y, angle, max_range)
```

## Generating benchmark maps

`MapGenerator` builds classic benchmarking patterns.

```python
from hivebr.engine.map_generator import MapGenerator

grid = MapGenerator.create_grid(type="u")      # "u", "l", "random"
MapGenerator.save(grid, "hivebr/engine/assets/mapa_u.png")
```

Patterns available:

| `type` | Description |
| ------ | ----------- |
| `u` | U-shaped corridor. |
| `l` | L-shaped corridor. |
| `random` | Randomised maze from a seed. |

See [MapGenerator API](api/map_generator.md) and
[OccupancyGridMap API](api/occupancy_grid.md).

!!! warning "Optional dependencies"
    Efficient inflation uses `scipy.ndimage.binary_dilation`, and image loading
    uses `Pillow`. Install them if you rely on occupancy grids.
