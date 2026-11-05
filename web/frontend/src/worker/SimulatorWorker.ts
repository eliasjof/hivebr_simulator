import type { SimConfig, SimStepResult, WorkerMessage, WorkerResponse } from '@/types'

type MessageCallback = (data: SimStepResult) => void
type ReadyCallback = () => void
type ErrorCallback = (error: string) => void

export class SimulatorWorker {
  private worker: Worker
  private stateCallbacks: Set<MessageCallback> = new Set()
  private readyCallbacks: Set<ReadyCallback> = new Set()
  private errorCallbacks: Set<ErrorCallback> = new Set()
  private pendingRequests: Map<number, { resolve: (value: any) => void; reject: (reason: any) => void }> = new Map()
  private requestId = 0

  constructor() {
    // Create worker from the Pyodide worker entry point
    this.worker = new Worker(
      new URL('../../pyodide/pyodide_worker.js', import.meta.url),
      { type: 'module', name: 'hivebr-pyodide-simulator' }
    )

    this.worker.onmessage = this.handleMessage.bind(this)
    this.worker.onerror = (error) => {
      console.error('Pyodide Worker error:', error)
      this.errorCallbacks.forEach(cb => cb(error.message))
    }
  }

  private handleMessage(event: MessageEvent<WorkerResponse>): void {
    const msg = event.data

    // Handle pending requests
    if (msg.id !== undefined && this.pendingRequests.has(msg.id)) {
      const { resolve, reject } = this.pendingRequests.get(msg.id)!
      this.pendingRequests.delete(msg.id)
      
      if (msg.success) {
        resolve(msg)
      } else {
        reject(new Error(msg.error || 'Unknown error'))
      }
      return
    }

    // Handle state updates (broadcast to all listeners)
    if (msg.type === 'state_update' && msg.data) {
      this.stateCallbacks.forEach(cb => cb(msg.data!))
    }

    // Handle ready signal
    if (msg.type === 'ready' || msg.type === 'worker_ready') {
      this.readyCallbacks.forEach(cb => cb())
    }

    // Handle Pyodide stdout/stderr
    if (msg.type === 'pyodide_stdout') {
      console.log('[Pyodide]', msg.data)
    }
    if (msg.type === 'pyodide_stderr') {
      console.warn('[Pyodide]', msg.data)
    }
  }

  private send<T>(type: WorkerMessage['type'], payload: Omit<WorkerMessage, 'type'>): Promise<T> {
    return new Promise((resolve, reject) => {
      const id = ++this.requestId
      this.pendingRequests.set(id, { resolve, reject })
      
      this.worker.postMessage({ type, ...payload, id })
      
      // Timeout after 60 seconds (Pyodide init can be slow)
      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id)
          reject(new Error(`Request ${type} timed out`))
        }
      }, 60000)
    })
  }

  async init(config: any, userCode: string): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('init', { config, user_code: userCode })
    if (!result.success) throw new Error(result.error || 'Init failed')
  }

  async step(dt: number, commands?: Record<string, any>): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('step', { dt, commands })
    if (!result.success) throw new Error(result.error || 'Step failed')
  }

  async setWaypoints(robotId: number, waypoints: number[][]): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('set_waypoints', { robot_id: robotId, waypoints })
    if (!result.success) throw new Error(result.error || 'Set waypoints failed')
  }

  async addObstacle(x: number, y: number, radius: number): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('add_obstacle', { x, y, radius })
    if (!result.success) throw new Error(result.error || 'Add obstacle failed')
  }

  async loadMap(imageBytes: Uint8Array, resolution: number): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('load_map', { 
      image_bytes: Array.from(imageBytes), 
      resolution 
    })
    if (!result.success) throw new Error(result.error || 'Load map failed')
  }

  async loadLineMap(imageBytes: Uint8Array, resolution: number): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('load_line_map', { 
      image_bytes: Array.from(imageBytes), 
      resolution 
    })
    if (!result.success) throw new Error(result.error || 'Load line map failed')
  }

  async reset(): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('reset', {})
    if (!result.success) throw new Error(result.error || 'Reset failed')
  }

  async exportLog(format: 'pkl' | 'csv'): Promise<Uint8Array> {
    const result = await this.send<{ success: boolean; data?: number[]; error?: string }>('export_log', { format })
    if (!result.success || !result.data) throw new Error(result.error || 'Export log failed')
    return new Uint8Array(result.data)
  }

  async updateConfig(config: Partial<any>): Promise<void> {
    const result = await this.send<{ success: boolean; error?: string }>('update_config', { config })
    if (!result.success) throw new Error(result.error || 'Update config failed')
  }

  onStateUpdate(callback: (data: SimStepResult) => void): () => void {
    this.stateCallbacks.add(callback)
    return () => this.stateCallbacks.delete(callback)
  }

  onReady(callback: ReadyCallback): () => void {
    this.readyCallbacks.add(callback)
    return () => this.readyCallbacks.delete(callback)
  }

  onError(callback: ErrorCallback): () => void {
    this.errorCallbacks.add(callback)
    return () => this.errorCallbacks.delete(callback)
  }

  terminate(): void {
    this.worker.terminate()
    this.stateCallbacks.clear()
    this.readyCallbacks.clear()
    this.errorCallbacks.clear()
    this.pendingRequests.forEach(({ reject }) => reject(new Error('Worker terminated')))
    this.pendingRequests.clear()
  }
}