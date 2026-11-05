import { useSimulatorStore } from '@/stores/simulatorStore'
import { useUIStore } from '@/stores/uiStore'

export function Toolbar() {
  const { running, setRunning, worker, config: _config, setConfig: _setConfig } = useSimulatorStore()
  const { theme: _theme, toggleTheme: _toggleTheme, togglePanel: _togglePanel, isPanelOpen } = useUIStore()

  const handleRun = async () => {
    if (!worker) return
    if (running) {
      // Pause - just stop stepping (handled by main loop)
      setRunning(false)
    } else {
      setRunning(true)
      // Start simulation loop
      runSimulationLoop()
    }
  }

  const handleReset = async () => {
    if (!worker) return
    await worker.reset()
    setRunning(false)
  }

  const handleStep = async () => {
    if (!worker) return
    await worker.step(0.03)
  }

  const runSimulationLoop = () => {
    const state = useSimulatorStore.getState()
    if (!state.running || !state.worker) return
    
    state.worker.step(0.03).then(() => {
      if (useSimulatorStore.getState().running) {
        requestAnimationFrame(runSimulationLoop)
      }
    })
  }

  const handleLoadMap = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.png,.jpg,.jpeg'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file && worker) {
        const arrayBuffer = await file.arrayBuffer()
        await worker.loadMap(new Uint8Array(arrayBuffer), 0.1)
      }
    }
    input.click()
  }

  const handleLoadTrack = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.png,.jpg,.jpeg'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (file && worker) {
        const arrayBuffer = await file.arrayBuffer()
        await worker.loadLineMap(new Uint8Array(arrayBuffer), 0.1)
      }
    }
    input.click()
  }

  return (
    <div className="toolbar">
      <div className="toolbar-group">
        <button className={`btn ${running ? 'btn-danger' : 'btn-primary'}`} onClick={handleRun}>
          {running ? '⏸ Pause' : '▶ Run'}
        </button>
        <button className="btn btn-secondary" onClick={handleStep} disabled={running}>
          ⏭ Step
        </button>
        <button className="btn btn-warning" onClick={handleReset}>
          ↻ Reset
        </button>
      </div>

      <div className="toolbar-group">
        <button className="btn btn-secondary" onClick={handleLoadMap} title="Load Occupancy Map">
          🗺️ Map
        </button>
        <button className="btn btn-secondary" onClick={handleLoadTrack} title="Load Line Track">
          🛤️ Track
        </button>
      </div>

      <div className="toolbar-group">
        <button className={`btn ${isPanelOpen('logs') ? 'btn-active' : 'btn-secondary'}`} onClick={() => _togglePanel('logs')}>
          📋 Logs
        </button>
        <button className={`btn ${isPanelOpen('plots') ? 'btn-active' : 'btn-secondary'}`} onClick={() => _togglePanel('plots')}>
          📊 Plots
        </button>
      </div>

      <div className="toolbar-spacer" />

      <div className="toolbar-group">
        <button className="btn btn-secondary" onClick={_toggleTheme} title="Toggle Theme">
          {_theme ===  'dark' ? '☀️' : '🌙'}
        </button>
        <button className="btn btn-secondary" onClick={() => navigator.clipboard.writeText(window.location.href)} title="Share URL">
          🔗 Share
        </button>
      </div>
    </div>
  )
}