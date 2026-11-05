import sys
import os
from pathlib import Path
# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))
sys.path.insert(0,str(project_root))
sys.path.insert(0,str(project_root / "src"))

from hivebr.engine import Simulator, load_config
from planners.planners import RRTPlanner, RRTStarPlanner, PRMPlanner, BITStarPlanner
from controllers.planner_controller import PlannerController
from hivebr.engine.map_generator import MapGenerator

config = load_config("config/default.yaml")
config["robot"]["type"] = "differential"

# Troque só o planner_class para mudar o algoritmo
ctrl = PlannerController(
    planner_class=RRTStarPlanner,
    planner_kwargs=dict(step_size=0.5, max_iter=10000, rewire_radius=2.0),
    robot_type="differential",
    robot_radius=config["robot"]["radius"],
    show_debug=True,   # mostra árvore/grafo
    show_path=True,
)

sim = Simulator(config=config, controller=ctrl.controller,
                draw_callback=ctrl.draw_callback)
sim.robot.set_initial_pose(1.0,1.0,0.0)
sim.set_using_orientation(False)
sim.robot.radius = 0.3
seed = 42
# grid = MapGenerator.create_grid(type='random', seed=seed, obstacle_rate=0.001)
grid, obstacles_list = MapGenerator.create_grid(
    width=200,
    height=200,
    seed=seed,
    obstacle_rate=0.25,
    robot_radius=sim.robot.radius,
    resolution=0.2,
    n_walls=15,
    wall_thickness=8,
    min_wall_length=20,
    type="circle",
    shape_type="circle"
)

print("Taxa ocupada:", grid.mean())
sim.set_map_from_grid(grid, resolution=0.2, name=f"mapa_{seed}.png")

for obs in obstacles_list:
    
    print(obs["x"], obs["y"], obs["r"])
    sim.world.add_obstacle(pos=[obs["x"], obs["y"]], radius=obs["r"])
sim.robot.set_battery_parameters(c_idle=0.01, c_v=0.05, c_w=0.02, critical_battery=40)



# Se quiser salvar para usar depois:
# MapGenerator.save_grid_to_png(grid, f"mapa_{seed}.png")
sim.run()