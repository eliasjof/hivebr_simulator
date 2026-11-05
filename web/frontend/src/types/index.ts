export interface RobotState {
  id: number
  x: number
  y: number
  theta: number
  v: number
  omega: number
  type: string
  radius: number
  battery: number
  goal: number[] | null
  max_speed?: number
  max_omega?: number
  wheel_base?: number
}

export interface SimConfig {
  window: {
    width: number
    height: number
    min_width: number
    min_height: number
    panel_width: number
    title: string
  }
  world: {
    width: number
    height: number
    grid_size: number
    obstacle_radius: number
    show_origin: boolean
    show_axes: boolean
    default_obstacle_radius: number
    obstacles: number[][]
  }
  camera: {
    initial_zoom: number
    min_zoom: number
    max_zoom: number
    zoom_step: number
    margin_x: number
    margin_y: number
  }
  robot: {
    type: string
    initial_pose: number[]
    radius: number
    length: number
    width: number
    wheel_base: number
    max_speed: number
    max_omega: number
    max_steer: number
    path_max_length: number
    tau_v: number
  }
  robots?: Array<{
    id?: number
    type?: string
    initial_pose?: number[]
    radius?: number
    length?: number
    width?: number
    wheel_base?: number
    max_speed?: number
    max_omega?: number
    max_steer?: number
    path_max_length?: number
    tau_v?: number
    color?: number[]
  }>
  lidar: {
    enabled: boolean
    num_rays: number
    range: number
    fov_deg: number
  }
  waypoints: {
    goal_tolerance: number
    define_orientation: boolean
    show_tolerance_circle: boolean
    points: number[][]
  }
  controller: Record<string, any>
  colors: Record<string, any>
  interaction: {
    collision_policy: string
    robot_collision: boolean
    robot_safety_margin: number
    resolve_push: number
    comm_radius: number | null
    show_robot_links: boolean
  }
  noise: {
    enabled: boolean
    sigma_v: number
    sigma_omega: number
    limit: number
    seed: number | null
  }
  obstacles: number[][]
  show_times: boolean
  theme: string
  running_simulation: boolean
  gui: {
    buttons: string[]
    sliders: string[]
  }
}

export interface SimStepResult {
  states: Record<string, RobotState>
  lidar: Record<string, number[][]>
  collisions: Record<string, boolean>
  sim_time: number
  collision_events: CollisionEvent[]
}

export interface CollisionEvent {
  t: number
  kind: 'robot' | 'obstacle' | 'grid'
  robots: number[]
  obstacle_index?: number
  obstacle_xy?: number[]
  distance?: number
}

export interface WorkerMessage {
  type: 'init' | 'step' | 'set_waypoints' | 'add_obstacle' | 'load_map' | 'load_line_map' | 'reset' | 'export_log' | 'update_config'
  id?: number
  config?: SimConfig | Record<string, any>
  user_code?: string
  dt?: number
  commands?: Record<string, any>
  robot_id?: number
  waypoints?: number[][]
  x?: number
  y?: number
  radius?: number
  image_bytes?: number[]
  resolution?: number
  format?: 'pkl' | 'csv'
}

export interface WorkerResponse {
  type?: 'ready' | 'state_update' | 'log_export' | 'error' | 'success' | 'worker_ready' | 'pyodide_stdout' | 'pyodide_stderr'
  success: boolean
  error?: string
  data?: SimStepResult
  log_data?: number[]
  format?: string
  id?: number
}

export interface SimulatorWorkerInterface {
  init: (config: SimConfig, userCode: string) => Promise<void>
  step: (dt: number, commands?: Record<string, any>) => Promise<void>
  setWaypoints: (robotId: number, waypoints: number[][]) => Promise<void>
  addObstacle: (x: number, y: number, radius: number) => Promise<void>
  loadMap: (imageBytes: Uint8Array, resolution: number) => Promise<void>
  loadLineMap: (imageBytes: Uint8Array, resolution: number) => Promise<void>
  reset: () => Promise<void>
  exportLog: (format: 'pkl' | 'csv') => Promise<Uint8Array>
  updateConfig: (config: Partial<Record<string, any>>) => Promise<void>
  onStateUpdate: (callback: (data: SimStepResult) => void) => () => void
  onReady: (callback: () => void) => () => void
  onError: (callback: (error: string) => void) => () => void
  terminate: () => void
}