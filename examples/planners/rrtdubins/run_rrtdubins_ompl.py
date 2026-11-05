import numpy as np
import matplotlib.pyplot as plt
from ompl import base as ob
from ompl import geometric as og

def is_state_valid(state):
    # Obstáculos definidos no exemplo (círculos)
    obstacle_list = [
        [-0.8, -0.2, 0.4],
        [0.0, 0.6, 0.4],
        [0.0, -0.9, 0.4],
        [0.8, 0.2, 0.4]
    ]
    robot_radius = 0.073
    for (ox, oy, size) in obstacle_list:
        if np.hypot(state.getX() - ox, state.getY() - oy) < (size + robot_radius):
            return False
    return True

def run_ompl_planning(start_pos, goal_pos, rrt_star=True):
    # Espaço Dubins: SE(2) - x, y, theta
    space = ob.DubinsStateSpace(0.73)  # raio mínimo 0.73
    bounds = ob.RealVectorBounds(2)
    bounds.setLow(-2.1)
    bounds.setHigh(1.6)
    space.asCompoundStateSpace().getSubspace(0).setBounds(bounds)
    
    si = ob.SpaceInformation(space)
    si.setStateValidityChecker(ob.StateValidityCheckerFn(is_state_valid))
    
    start = ob.State(space)
    start().setXY(start_pos[0], start_pos[1])
    start().setYaw(start_pos[2])
    
    goal = ob.State(space)
    goal().setXY(goal_pos[0], goal_pos[1])
    goal().setYaw(goal_pos[2])
    
    pdef = ob.ProblemDefinition(si)
    pdef.setStartAndGoalStates(start, goal)
    
    if rrt_star:
        planner = og.RRTstar(si)
    else:
        planner = og.RRT(si)
        
    planner.setProblemDefinition(pdef)
    planner.setup()
    
    solved = planner.solve(5.0) # 5 segundos de tempo limite
    
    if solved:
        return pdef.getSolutionPath()
    return None

def main():
    start = [-1.80, -0.50, np.deg2rad(0.0)]
    goal = [1.50, 0.80, np.deg2rad(45.0)]
    
    print("Planejando com RRT* Dubins OMPL...")
    path = run_ompl_planning(start, goal, rrt_star=True)
    
    if path:
        print("Caminho encontrado!")
        # Extrair estados para visualização
        states = path.getStates()
        x = [s.getX() for s in states]
        y = [s.getY() for s in states]
        
        plt.figure(figsize=(8, 8))
        plt.plot(x, y, label="OMPL Dubins RRT*")
        plt.grid(True)
        plt.legend()
        plt.show()
    else:
        print("Falha ao encontrar caminho.")

if __name__ == '__main__':
    main()
