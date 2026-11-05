// Simulator Web Worker - Mock Version for Development
// This mocks the simulation in JavaScript for development
// Will be replaced with Pyodide-based Python simulation later

import type { WorkerMessage, WorkerResponse, SimStepResult, SimConfig, RobotState } from '@/types'

// Use the global RobotState type from types/index.ts
interface SimulatorState {
  config: SimConfig | null
  robots: RobotState[]
  waypoints: Record<string, number[][]>
  simTime: number
  running: boolean
}

// Simple physics simulation
function simulateStep(state: SimulatorState, dt: number, commands: Record<string, any>): SimulatorState {
  const newRobots = state.robots.map(robot => {
    const cmd = commands[robot.id] || {}
    const robotType = robot.type
    
    let v = 0, omega = 0
    
    if (robotType === 'holonomic') {
      v = Math.hypot(cmd.vx || 0, cmd.vy || 0)
      omega = 0
    } else if (robotType === 'ackermann') {
      v = cmd.speed || 0
      omega = (v / (robot.wheel_base || 0.5)) * Math.tan(cmd.steer || 0)
    } else {
      v = cmd.v || 0
      omega = cmd.omega || 0
    }

    // Clamp velocities
    const maxSpeed = robot.max_speed ?? 3.0
    v = Math.max(-maxSpeed, Math.min(maxSpeed, v))
    omega = Math.max(-(robot.max_omega ?? 4.0), Math.min(robot.max_omega ?? 4.0, omega))

    const newX = robot.x + v * Math.cos(robot.theta) * dt
    const newY = robot.y + v * Math.sin(robot.theta) * dt
    const newTheta = (robot.theta + omega * dt + Math.PI) % (2 * Math.PI) - Math.PI

    return { ...robot, x: newX, y: newY, theta: newTheta, v, omega }
  })

  // Check collisions
  const collisions: Record<string, boolean> = {}
  for (let i = 0; i < newRobots.length; i++) {
    for (let j = i + 1; j < newRobots.length; j++) {
      const dx = newRobots[i].x - newRobots[j].x
      const dy = newRobots[i].y - newRobots[j].y
      const dist = Math.hypot(dx, dy)
      if (dist < newRobots[i].radius + newRobots[j].radius) {
        collisions[newRobots[i].id] = true
        collisions[newRobots[j].id] = true
      }
    }
  }

  // LiDAR simulation (simplified)
  const lidar: Record<string, Array<[number, number, [number, number]]>> = {}
  for (const robot of newRobots) {
    const readings: Array<[number, number, [number, number]]> = []
    const numRays = 36
    for (let r = 0; r < numRays; r++) {
      const angle = robot.theta + (r / numRays) * 2 * Math.PI
      // Simplified: just return max range
      readings.push([angle, 12.0, [robot.x + 12 * Math.cos(angle), robot.y + 12 * Math.sin(angle)]])
    }
    lidar[robot.id] = readings
  }

  return {
    ...state,
    robots: newRobots,
    simTime: state.simTime + dt,
  }
}

// Global state
let simulatorState: SimulatorState = {
  config: null,
  robots: [],
  waypoints: {},
  simTime: 0,
  running: false,
}

// Initialize from config
function initFromConfig(config: SimConfig) {
  const robotsConfig = config.robots || [config.robot]
  
  simulatorState = {
    config,
    robots: robotsConfig.map((rc: any, i: number) => ({
      id: i,
      x: rc.initial_pose?.[0] || 2.5,
      y: rc.initial_pose?.[1] || 2.5,
      theta: rc.initial_pose?.[2] || 0,
      v: 0,
      omega: 0,
      type: rc.type || 'differential',
      radius: rc.radius || 0.25,
      max_speed: rc.max_speed || 3.0,
      max_omega: rc.max_omega || 4.0,
      wheel_base: rc.wheel_base || 0.5,
      battery: 100,
      goal: null,
    })),
    waypoints: {},
    simTime: 0,
    running: false,
  }

  // Set waypoints from config
  if (config.robots) {
    config.robots.forEach((rc: any, i: number) => {
      if (rc.waypoints) {
        simulatorState.waypoints[i] = rc.waypoints
        if (rc.waypoints.length > 0) {
          simulatorState.robots[i].goal = rc.waypoints[0]
        }
      }
    })
  }
}

function getStates(): Record<string, RobotState> {
  const states: Record<string, RobotState> = {}
  for (const robot of simulatorState.robots) {
    states[robot.id] = {
      id: robot.id,
      x: robot.x,
      y: robot.y,
      theta: robot.theta,
      v: robot.v,
      omega: robot.omega,
      type: robot.type,
      radius: robot.radius,
      battery: robot.battery,
      goal: robot.goal,
    }
  }
  return states
}

function getLidar(): Record<string, number[][]> {
  const lidar: Record<string, number[][]> = {}
  for (const robot of simulatorState.robots) {
    const readings: number[][] = []
    const numRays = 36
    for (let r = 0; r < numRays; r++) {
      const angle = robot.theta + (r / numRays) * 2 * Math.PI
      const hitX = robot.x + 12 * Math.cos(angle)
      const hitY = robot.y + 12 * Math.sin(angle)
      readings.push([angle, 12.0, hitX, hitY])
    }
    lidar[robot.id] = readings
  }
  return lidar
}

function getCollisions(): Record<string, boolean> {
  const collisions: Record<string, boolean> = {}
  for (let i = 0; i < simulatorState.robots.length; i++) {
    for (let j = i + 1; j < simulatorState.robots.length; j++) {
      const dx = simulatorState.robots[i].x - simulatorState.robots[j].x
      const dy = simulatorState.robots[i].y - simulatorState.robots[j].y
      const dist = Math.hypot(dx, dy)
      if (dist < simulatorState.robots[i].radius + simulatorState.robots[j].radius) {
        collisions[simulatorState.robots[i].id] = true
        collisions[simulatorState.robots[j].id] = true
      }
    }
  }
  return collisions
}

// Message handler
self.onmessage = async (event: MessageEvent<WorkerMessage>) => {
  const msg = event.data
  const id = msg.id

  let result: WorkerResponse = { success: true }

  try {
    switch (msg.type) {
      case 'init': {
        initFromConfig(msg.config! as SimConfig)
        result = { success: true, type: 'ready' }
        break
      }

      case 'step': {
        if (!simulatorState.running) {
          simulatorState.running = true
        }
        const commands = msg.commands || {}
        simulatorState = simulateStep(simulatorState, msg.dt!, commands)
        
        const stepResult: SimStepResult = {
          states: getStates(),
          lidar: getLidar(),
          collisions: getCollisions(),
          sim_time: simulatorState.simTime,
          collision_events: [],
        }
        
        result = { success: true }
        // Also send state update
        self.postMessage({ type: 'state_update', data: stepResult })
        break
      }

      case 'set_waypoints': {
        if (msg.robot_id !== undefined && msg.waypoints) {
          simulatorState.waypoints[msg.robot_id] = msg.waypoints
          if (msg.waypoints.length > 0) {
            simulatorState.robots[msg.robot_id].goal = msg.waypoints[0]
          }
        }
        result = { success: true }
        break
      }

      case 'add_obstacle': {
        // For mock, just acknowledge
        result = { success: true }
        break
      }

      case 'load_map': {
        result = { success: true }
        break
      }

      case 'load_line_map': {
        result = { success: true }
        break
      }

      case 'reset': {
        if (simulatorState.config) {
          initFromConfig(simulatorState.config)
        }
        result = { success: true }
        break
      }

      case 'export_log': {
        result = { success: true, log_data: [], format: msg.format || 'pkl' } as WorkerResponse
        break
      }

      case 'update_config': {
        if (msg.config && simulatorState.config) {
          simulatorState.config = { ...simulatorState.config, ...msg.config }
        }
        result = { success: true }
        break
      }

      default:
        result = { success: false, error: 'Unknown message type: ' + msg.type }
    }

    if (id !== undefined) {
      self.postMessage({ ...result, id })
    }

  } catch (error: unknown) {
    const err = error as Error
    const errorResult = { success: false, error: err.message, type: err.name }
    if (id !== undefined) {
      self.postMessage({ ...errorResult, id })
    } else {
      self.postMessage({ type: 'error', data: errorResult })
    }
  }
}

// Signal ready
self.postMessage({ type: 'worker_ready' })