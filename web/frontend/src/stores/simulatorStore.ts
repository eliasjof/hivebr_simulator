import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type { RobotState, SimConfig } from '@/types'
import type { SimulatorWorkerInterface } from '@/worker'

interface LogEntry {
  id: number
  timestamp: number
  message: string
  level: 'info' | 'warn' | 'error'
}

interface SimulatorState {
  // Worker
  worker: SimulatorWorkerInterface | null
  setWorker: (worker: SimulatorWorkerInterface) => void

  // Config
  config: SimConfig
  setConfig: (config: SimConfig) => void
  updateConfig: (partial: Partial<SimConfig>) => void

  // User code
  userCode: string
  setUserCode: (code: string) => void

  // Simulation state
  running: boolean
  setRunning: (running: boolean) => void
  simTime: number
  setSimTime: (time: number) => void

  // Robot states
  states: Record<string, RobotState>
  setStates: (states: Record<string, RobotState>) => void

  // Collisions
  collisions: Record<string, boolean>
  setCollisions: (collisions: Record<string, boolean>) => void

  // LiDAR
  lidar: Record<string, number[][]>
  setLidar: (lidar: Record<string, number[][]>) => void

  // Logs
  logs: LogEntry[]
  addLog: (message: string, level?: 'info' | 'warn' | 'error') => void
  clearLogs: () => void

  // Selected robot
  selectedRobot: number
  setSelectedRobot: (id: number) => void
}

let logId = 0

export const useSimulatorStore = create<SimulatorState>()(
  subscribeWithSelector((set) => ({
    // Worker
    worker: null,
    setWorker: (worker: SimulatorWorkerInterface) => set({ worker }),

    // Config
    config: {} as SimConfig,
    setConfig: (config) => set({ config }),
    updateConfig: (partial) => set((state) => ({ config: { ...state.config, ...partial } })),

    // User code
    userCode: '',
    setUserCode: (code) => set({ userCode: code }),

    // Simulation state
    running: false,
    setRunning: (running) => set({ running }),
    simTime: 0,
    setSimTime: (time) => set({ simTime: time }),

    // Robot states
    states: {},
    setStates: (states) => set({ states }),

    // Collisions
    collisions: {},
    setCollisions: (collisions) => set({ collisions }),

    // LiDAR
    lidar: {},
    setLidar: (lidar) => set({ lidar }),

    // Logs
    logs: [],
    addLog: (message, level = 'info') =>
      set((state) => ({
        logs: [...state.logs, { id: logId++, timestamp: Date.now(), message, level }],
      })),
    clearLogs: () => set({ logs: [] }),

    // Selected robot
    selectedRobot: 0,
    setSelectedRobot: (id) => set({ selectedRobot: id }),
  }))
)