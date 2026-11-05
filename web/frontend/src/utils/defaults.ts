export const defaultConfig = {
  window: {
    width: 1400,
    height: 750,
    min_width: 1100,
    min_height: 650,
    panel_width: 300,
    title: 'NavSim2D Web',
  },
  world: {
    width: 20.0,
    height: 12.0,
    grid_size: 1.0,
    obstacle_radius: 0.4,
    show_origin: true,
    show_axes: true,
    default_obstacle_radius: 0.4,
    obstacles: [
      [6.0, 5.0, 1.2],
      [13.16, 5.71, 0.4],
    ],
  },
  camera: {
    initial_zoom: 1.0,
    min_zoom: 0.25,
    max_zoom: 8.0,
    zoom_step: 1.1,
    margin_x: 1.0,
    margin_y: 1.0,
  },
  robot: {
    type: 'differential',
    initial_pose: [2.5, 2.5, 0.0],
    radius: 0.1375,
    length: 0.39,
    width: 0.275,
    wheel_base: 0.285,
    max_speed: 3.0,
    max_omega: 4.0,
    max_steer: 0.52,
    path_max_length: 4000,
    tau_v: 0.2,
  },
  lidar: {
    enabled: false,
    num_rays: 101,
    range: 12.0,
    fov_deg: 360,
  },
  waypoints: {
    goal_tolerance: 0.5,
    define_orientation: false,
    show_tolerance_circle: false,
    points: [],
  },
  controller: {
    enabled: true,
    attractive_gain: 1.0,
    repulsive_gain: 2.0,
    repulsive_radius: 2.0,
    max_repulsive_force: 8.0,
    force_filter_alpha: 0.35,
    command_filter_alpha: 0.4,
    obstacle_slowdown_distance: 2.0,
    min_obstacle_speed_factor: 0.2,
    min_lidar_distance: 0.08,
    linear_gain: 0.6,
    angular_gain: 0.6,
    max_steer_rate: 0.52,
    curvature_speed_gain: 2.0,
    tangential_gain: 1.5,
    stagnation_radius: 0.15,
    local_minima_angle_deg: 90.0,
    virtual_subgoal_offset: 2.0,
    emergency_brake_distance: 0.5,
    emergency_safe_distance: 0.65,
    emergency_rear_clearance: 0.5,
    reverse_speed: -0.25,
    reverse_duration_s: 1.2,
  },
  colors: {
    background: [30, 30, 30],
    grid: [50, 50, 50],
    panel: [20, 20, 20],
    robot: [30, 144, 255],
    obstacle: [40, 120, 40],
    waypoint: [255, 140, 0],
    goal: [57, 255, 20],
    path: [30, 144, 255],
    lidar: [0, 255, 255],
    red: [220, 50, 50],
    green: [0, 255, 0],
    white: [255, 255, 255],
    black: [0, 0, 0],
    silver: [192, 192, 186],
    fleet: [
      [30, 144, 255],
      [220, 20, 60],
      [50, 205, 50],
      [255, 165, 0],
      [148, 0, 211],
      [0, 206, 209],
      [255, 105, 180],
      [255, 215, 0],
    ],
  },
  interaction: {
    collision_policy: 'stop',
    robot_collision: true,
    robot_safety_margin: 0.0,
    resolve_push: 0.05,
    comm_radius: null,
    show_robot_links: false,
  },
  noise: {
    enabled: false,
    sigma_v: 0.0,
    sigma_omega: 0.0,
    limit: 3.0,
    seed: null,
  },
  obstacles: [],
  show_times: true,
  theme: 'dark',
  running_simulation: false,
  gui: {
    buttons: [
      'start',
      'reset',
      'clear_path',
      'clear_waypoints',
      'clear_obstacles',
      'load_map',
      'draw_track',
      'apply_track',
      'clear_track',
      'toggle_lidar',
      'toggle_noise',
      'toggle_times',
      'toggle_theme',
      'save_config',
      'center_camera',
      'plot_log',
      'export_log',
      'reset_logger',
    ],
    sliders: [
      'max_speed',
      'max_omega',
      'max_steer',
      'grid_size',
      'noise_sigma',
      'servo_max_speed',
    ],
  },
}

export const defaultUserCode = `from hivebr import HiveBrAgent, SwarmExperiment
import numpy as np

class PatrolAgent(HiveBrAgent):
    """Agente de patrulha simples usando controle proporcional."""
    
    def setup(self):
        self.kp = self.params.get("kp", 0.5)
        self.r_tol = float((self.cfg or {}).get("waypoints", {}).get("goal_tolerance", 0.5))
    
    def loop(self, state, neighbors):
        goal = state.goal
        if goal is None:
            return (0.0, 0.0)
        
        dx = goal[0] - state.x
        dy = goal[1] - state.y
        dist = np.hypot(dx, dy)
        
        if dist < self.r_tol:
            return (0.0, 0.0)
        
        target_angle = np.arctan2(dy, dx)
        angle_error = target_angle - state.theta
        # Normalizar para [-pi, pi]
        angle_error = (angle_error + np.pi) % (2 * np.pi) - np.pi
        
        v = self.kp * dist
        omega = 2.0 * angle_error
        
        return (v, omega)

# Configuração do experimento
config = {
    "robots": 2,
    "backend": "navsim2d",
    "dt": 0.03,
    "orientation": True,
    "agent_classes": {
        0: "PatrolAgent",
        1: "PatrolAgent",
    },
    "agent_params": {
        0: {"kp": 0.5},
        1: {"kp": 0.3},
    },
    "routes": {
        0: [[5, 2, 0.0], [5, 6, 0.0], [2, 6, 0.0], [2, 2, 0.0]],
        1: [[10, 5, 0.0], [10, 9, 0.0], [5, 9, 0.0], [5, 5, 0.0]],
    }
}

# Para usar controller centralizado, descomente abaixo:
# class CentralController(SwarmController):
#     def loop(self, states):
#         commands = {}
#         for rid, state in states.items():
#             goal = state.goal
#             if goal is None:
#                 commands[rid] = {"v": 0.0, "omega": 0.0}
#                 continue
#             # ... lógica de controle centralizado
#         return commands
# 
# config["controller_class"] = "CentralController"
`