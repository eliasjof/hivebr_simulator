import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0,str(project_root))
sys.path.insert(0,str(project_root / "src"))

from hivebr.engine.simulator import Simulator
from hivebr.engine.config import load_config
from examples.controllers.potential_field import potential_field_controller
from hivebr.engine.map_generator import MapGenerator

def run_maze_simulation():
    # Load configuration
    config_path = project_root / "config" / "maze_config.yaml"
    config = load_config(config_path)
    
    # Initialize simulator
    # We pass the potential field controller as an example
    sim = Simulator(config=config, controller=potential_field_controller)
    sim.set_using_orientation(False)
    
    sim.robot.set_initial_pose(0.0,0.0,0.0)

    grid = MapGenerator.create_grid(type='u')
    sim.set_map_from_grid(grid, resolution=0.1, name="mapa_u.png")

    # Se quiser salvar para usar depois:
    MapGenerator.save_grid_to_png(grid, "hivebr/engine/assets/mapa_u.png")
    
    print("Maze simulation running. Use right-click to add obstacles, left-click to set waypoints.")
    sim.run()

if __name__ == "__main__":
    run_maze_simulation()
