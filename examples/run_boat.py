from hivebr.engine import Simulator, load_config
from planners.astar import AStarPlanner
import numpy as np

from controllers.waypoint_follower_controller import (
    waypoint_follower_controller
)

config = load_config("config/default.yaml")
config["robot"]["type"] = "boat"

sim = Simulator(
    config=config,
    controller=waypoint_follower_controller
)

planner = AStarPlanner(
    bounds=(
        0,
        sim.world.width,
        0,
        sim.world.height
    ),
    resolution=sim.world.grid_size,
    robot_radius=sim.robot.radius
)
points_o = np.array([[5,7, 0]])
points_o = np.array(points_o)
# print(points_o)
# points =  np.c_[points, np.nan*np.ones(len(points))]    
# sim.waypoints.waypoints = list(points)
sim.waypoints.waypoints = list(points_o)
goal = sim.waypoints.waypoints[-1][:2]
print(goal)

last_signature = None

while sim.running:

    signature = sim.get_planning_signature()

    if signature != last_signature:

        print("Replanning...")
        planner = AStarPlanner(
            bounds=(
                0,
                sim.world.width,
                0,
                sim.world.height
            ),
            resolution=sim.world.grid_size,
            robot_radius=sim.robot.radius
        )

        goal = sim.waypoints.waypoints[-1][:2]

        path, occ = planner.plan(
            start=sim.robot.position,
            goal=goal,
            obstacles=sim.world.obstacles
        )
        print(path)

        if path is not None:

            # sim.waypoints.clear()

            for p in path:
                sim.waypoints.add_waypoint(p)

        last_signature = signature

    sim.step()