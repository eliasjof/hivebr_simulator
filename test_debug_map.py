"""Debug test for occupancy map."""
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'web/pyodide/worker')

from hivebr.engine.core import DEFAULT_CONFIG
from copy import deepcopy
from web_simulator import WebSimulator
import numpy as np
from PIL import Image
from io import BytesIO


config = deepcopy(DEFAULT_CONFIG)
config["robots"] = [
    {"id": 0, "type": "differential", "initial_pose": [1.0, 5.0, 0.0], "radius": 0.25},
]
config["dt"] = 0.03

# Create a test occupancy map: 10x10m with a horizontal wall at y=5
map_array = np.zeros((100, 100), dtype=np.uint8)
map_array[:, :] = 255  # White = free
map_array[45:55, :] = 0  # Black wall at y=5m (rows 45-55)

img = Image.fromarray(map_array, mode='L')
buf = BytesIO()
img.save(buf, format='PNG')
map_bytes = list(buf.getvalue())

sim = WebSimulator()
result = sim.init(config, "")
print(f"Init result: {result}")

# Load map
result = sim.load_occupancy_map(map_bytes, 0.1)
print(f"Load map result: {result}")

# Debug: check world grid
print(f"World grid_map: {sim.core.world.grid_map is not None}")
if sim.core.world.grid_map:
    print(f"  grid shape: {sim.core.world.grid_map.grid.shape}")
    print(f"  inflated shape: {sim.core.world.grid_map.inflated_grid.shape}")
    # Check occupancy at robot position
    print(f"  is_occupied(1.0, 5.0): {sim.core.world.grid_map.is_occupied(1.0, 5.0)}")
    print(f"  is_occupied(1.0, 5.0, inflated): {sim.core.world.grid_map.is_occupied(1.0, 5.0, use_inflated=True)}")

# Test collision with wall
print("Testing collision with wall...")
for i in range(5):
    step_result = sim.step(0.03, external_commands={"0": {"v": 1.0, "omega": 0.0}})
    print(f"Step {i} result: {step_result}")
    if not step_result.get("success"):
        print(f"  ERROR: {step_result.get('error')}")
        break
    print(f"  pos=({step_result['states']['0']['x']:.2f}, {step_result['states']['0']['y']:.2f}), collision={step_result['collisions']}")