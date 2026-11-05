from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
from hivebr.engine import Simulator, load_config
from examples.controllers.potential_field import potential_field_controller
from examples.planners.astar import AStarPlanner




if __name__ == "__main__":
    config = load_config(ROOT / "config" / "default.yaml")
    config["robot"]["type"] = "ackermann"
    sim = Simulator(config=config, controller=potential_field_controller)
    sim.set_goal_tolerance(0.1)
    sim.run()
    
