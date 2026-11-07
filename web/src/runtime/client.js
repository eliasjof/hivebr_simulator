// Main-thread client for the simulation worker.
import { allocRing, RingWriter } from './ring.js'

export const DEFAULT_PYODIDE_URL = 'https://cdn.jsdelivr.net/pyodide/v0.29.0/full/'
const STOP_INTERRUPT_MS = 1500
const STOP_TERMINATE_MS = 1500

function resolveUrl(rel) {
  return new URL(rel, document.baseURI).href
}

export class SimClient {
  constructor(options = {}) {
    this.pyodideUrl = options.pyodideUrl || import.meta.env.VITE_PYODIDE_URL || DEFAULT_PYODIDE_URL
    if (!this.pyodideUrl.endsWith('/')) this.pyodideUrl += '/'
    this.zipUrl = options.zipUrl || resolveUrl(`${import.meta.env.BASE_URL}hivebr-py.zip`)
    this.state = 'booting'
    this.interactive = false
    this.worker = null
    this.sab = null
    this.writer = null
    this._listeners = new Map()
    this._lastFrameRaw = null
    this._readyWaiters = []
    this._runWaiter = null
    this._files = new Map()
    this._fileId = 0
    this._clientConfig = options.clientConfig || null
    this._stopTimers = []
    this._stopWaiters = []
  }

  // ---- events ------------------------------------------------------------
  // Events: boot, ready, stdout, stderr, run_started, finished, fatal,
  // scene, frame, log_data, file, figure, notice, state, restart.
  // Listeners receive the parsed payload (JSON strings are parsed only if a listener exists).
  on(type, fn) {
    let set = this._listeners.get(type)
    if (!set) this._listeners.set(type, (set = new Set()))
    set.add(fn)
    return () => set.delete(fn)
  }
  off(type, fn) {
    const set = this._listeners.get(type)
    if (set) set.delete(fn)
  }
  _emit(type, payload) {
    const set = this._listeners.get(type)
    if (!set || set.size === 0) return
    for (const fn of [...set]) {
      try { fn(payload) } catch (e) { console.error(`listener "${type}" failed`, e) }
    }
  }
  _emitRaw(type, payload) {
    const set = this._listeners.get(type)
    if (!set || set.size === 0) return
    const parsed = typeof payload === 'string' ? JSON.parse(payload) : payload
    for (const fn of [...set]) {
      try { fn(parsed) } catch (e) { console.error(`listener "${type}" failed`, e) }
    }
  }
  _setState(s) {
    if (this.state === s) return
    this.state = s
    this._emit('state', s)
  }

  /** Latest frame (parsed on demand); frames are never queued. */
  get lastFrame() {
    return this._lastFrameRaw == null ? null : JSON.parse(this._lastFrameRaw)
  }

  // ---- lifecycle ---------------------------------------------------------
  /** Boots the worker. Resolves with the `ready` payload; rejects on fatal. */
  init() {
    if (this.worker) return this._readyPromise()
    this._setState('booting')
    const isolated = typeof SharedArrayBuffer !== 'undefined' && globalThis.crossOriginIsolated
    this.sab = isolated ? allocRing() : null
    this.writer = this.sab ? new RingWriter(this.sab.ring, this.sab.control) : null
    const worker = new Worker(new URL('./sim.worker.js', import.meta.url), { type: 'module' })
    this.worker = worker
    worker.onmessage = (ev) => this._onMessage(worker, ev.data)
    worker.onerror = (ev) => {
      this._onMessage(worker, { type: 'fatal', payload: { message: ev.message || 'Worker error' } })
    }
    const p = this._readyPromise()
    worker.postMessage({ type: 'init', zipUrl: this.zipUrl, sab: this.sab, pyodideUrl: this.pyodideUrl, clientConfig: this._clientConfig })
    return p
  }

  _readyPromise() {
    if (this.state === 'ready' || this.state === 'running') return Promise.resolve(this._readyInfo)
    return new Promise((resolve, reject) => this._readyWaiters.push({ resolve, reject }))
  }

  _onMessage(worker, msg) {
    if (worker !== this.worker || !msg) return
    const { type, payload } = msg
    switch (type) {
      case 'frame':
        this._lastFrameRaw = payload
        this._emitRaw('frame', payload)
        return
      case 'ready':
        this.interactive = !!payload.interactive
        this._readyInfo = payload
        this._setState('ready')
        this._emit('ready', payload)
        this._readyWaiters.splice(0).forEach((w) => w.resolve(payload))
        return
      case 'run_started':
        this._setState(this.state === 'stopping' ? 'stopping' : 'running')
        this._emit('run_started', payload)
        return
      case 'finished':
        this._clearStopTimers()
        this._setState('ready')
        this._emit('finished', payload)
        if (this._runWaiter) { this._runWaiter.resolve(payload); this._runWaiter = null }
        this._stopWaiters.splice(0).forEach((r) => r(payload))
        return
      case 'fatal':
        this._clearStopTimers()
        this._setState('error')
        this._emit('fatal', payload)
        this._readyWaiters.splice(0).forEach((w) => w.reject(new Error(payload.message)))
        if (this._runWaiter) { this._runWaiter.reject(new Error(payload.message)); this._runWaiter = null }
        this._stopWaiters.splice(0).forEach((r) => r(null))
        return
      case 'file_content': {
        const w = this._files.get(payload.id)
        if (!w) return
        this._files.delete(payload.id)
        if (payload.b64 == null) w.reject(new Error(payload.error || 'File not found'))
        else w.resolve(Uint8Array.from(atob(payload.b64), (c) => c.charCodeAt(0)))
        return
      }
      case 'client_config': {
        const p = typeof payload === 'string' ? JSON.parse(payload) : payload
        // Remember the latest config so a worker restart keeps using it.
        this._clientConfig = (!p.reset && p.b64) ? { path: p.path, b64: p.b64 } : null
        this._emit('client_config', p)
        return
      }
      default:
        this._emitRaw(type, payload)
    }
  }

  // ---- running -----------------------------------------------------------
  /** Runs user code. Resolves with the `finished` payload. */
  run(code, { autostart = true } = {}) {
    if (this.state !== 'ready') return Promise.reject(new Error(`Simulator is not ready (${this.state})`))
    this._setState('running')
    if (this.sab) new Uint8Array(this.sab.interrupt)[0] = 0
    return new Promise((resolve, reject) => {
      this._runWaiter = { resolve, reject }
      this.worker.postMessage({ type: 'run', code, autostart })
    })
  }

  /** Sends a UI command ({cmd, ...}) to the running Python. Returns false if not delivered. */
  send(cmd) {
    if (!this.writer || (this.state !== 'running' && this.state !== 'stopping')) return false
    return this.writer.push(JSON.stringify(cmd))
  }

  /**
   * Stops the run with three escalation levels: `stop` command, KeyboardInterrupt
   * through the interrupt buffer, and finally terminating the worker and rebooting.
   * Resolves when the run ended (or the worker restarted).
   */
  stop() {
    if (this.state !== 'running') return Promise.resolve(null)
    this._setState('stopping')
    const done = new Promise((resolve) => this._stopWaiters.push(resolve))
    if (!this.writer) {
      this._terminateAndRestart('Simulation stopped by restarting the interpreter.', 'restart_stop')
      return done
    }
    this.writer.push(JSON.stringify({ cmd: 'stop' }))
    this._stopTimers.push(setTimeout(() => {
      new Uint8Array(this.sab.interrupt)[0] = 2
      this._stopTimers.push(setTimeout(() => {
        this._terminateAndRestart('The code did not respond; the interpreter was restarted.', 'restart_unresponsive')
      }, STOP_TERMINATE_MS))
    }, STOP_INTERRUPT_MS))
    return done
  }

  _clearStopTimers() {
    this._stopTimers.splice(0).forEach(clearTimeout)
  }

  _terminateAndRestart(text, code) {
    this._clearStopTimers()
    if (this.worker) this.worker.terminate()
    this.worker = null
    this.sab = null
    this.writer = null
    const finished = { ok: false, stopped: true, error: null, files: [] }
    this._files.forEach((w) => w.reject(new Error('Interpreter restarted')))
    this._files.clear()
    this._emit('notice', { level: 'warn', text, code })
    this._setState('booting')
    this._emit('finished', finished)
    if (this._runWaiter) { this._runWaiter.resolve(finished); this._runWaiter = null }
    this._stopWaiters.splice(0).forEach((r) => r(finished))
    this._emit('restart', {})
    this.init().catch(() => { /* reported through the `fatal` event */ })
  }

  /** Reads a file from the Pyodide filesystem. */
  readFile(path) {
    if (!this.worker) return Promise.reject(new Error('Worker unavailable'))
    const id = ++this._fileId
    return new Promise((resolve, reject) => {
      this._files.set(id, { resolve, reject })
      this.worker.postMessage({ type: 'read_file', id, path })
    })
  }

  dispose() {
    this._clearStopTimers()
    if (this.worker) this.worker.terminate()
    this.worker = null
  }
}
