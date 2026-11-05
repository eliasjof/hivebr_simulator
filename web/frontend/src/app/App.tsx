import { useEffect, useRef, useState } from 'react'
import { EditorPanel } from '@/editor/EditorPanel'
import { SimulatorView } from '@/renderer/SimulatorView'
import { Toolbar } from '@/ui/Toolbar'
import { SidePanel } from '@/ui/SidePanel'
import { StatusBar } from '@/ui/StatusBar'
import { LogPanel } from '@/ui/LogPanel'
import { PlotPanel } from '@/ui/PlotPanel'
import { useSimulatorStore } from '@/stores/simulatorStore'
import { useUIStore } from '@/stores/uiStore'
import { WorkerClient } from '@/worker'
import { SimStepResult } from '@/types'
import { defaultConfig, defaultUserCode } from '@/utils/defaults'
import { decodeExperimentFromURL, encodeExperimentToURL } from '@/utils/urlCodec'

function App() {
  const workerRef = useRef<WorkerClient | null>(null)
  const [initialized, setInitialized] = useState(false)
  const { setWorker, setRunning, setSimTime, setStates, setCollisions, setLidar, addLog, setConfig } = useSimulatorStore()
  const { theme, isPanelOpen } = useUIStore()

  useEffect(() => {
    // Initialize worker
    const worker = new WorkerClient()
    workerRef.current = worker
    setWorker(worker)

    // Set up message handlers
    worker.onStateUpdate((data: SimStepResult) => {
      setSimTime(data.sim_time)
      setStates(data.states)
      setCollisions(data.collisions)
      setLidar(data.lidar)
      if (data.collision_events?.length) {
        data.collision_events.forEach((evt: any) => {
          addLog(`[${evt.t.toFixed(2)}s] Collision: ${evt.kind}`, 'warn')
        })
      }
    })

    worker.onReady(() => {
      addLog('Simulator ready', 'info')
      setInitialized(true)
    })

    worker.onError((error: string) => {
      addLog(`Worker error: ${error}`, 'error')
    })

    // Load from URL or use defaults
    const urlParams = decodeExperimentFromURL()
    const initialConfig = urlParams?.config || defaultConfig
    const initialCode = urlParams?.code || defaultUserCode

    worker.init(initialConfig, initialCode)
    setConfig(initialConfig)

    // Update URL when config/code changes (debounced)
    let urlUpdateTimeout: ReturnType<typeof setTimeout>
    const updateURL = () => {
      clearTimeout(urlUpdateTimeout)
      urlUpdateTimeout = setTimeout(() => {
        const state = useSimulatorStore.getState()
        const code = state.userCode || defaultUserCode
        encodeExperimentToURL({ config: state.config, code })
      }, 500)
    }

    // Subscribe to config/code changes
    const unsubConfig = useSimulatorStore.subscribe(
      (s) => s.config,
      updateURL
    )
    const unsubCode = useSimulatorStore.subscribe(
      (s) => s.userCode,
      updateURL
    )

    return () => {
      worker.terminate()
      unsubConfig()
      unsubCode()
    }
  }, [setWorker, setRunning, setSimTime, setStates, setCollisions, setLidar, addLog, setConfig])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  if (!initialized) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Inicializando simulador...</p>
      </div>
    )
  }

  return (
    <div className="app-layout">
      <Toolbar />
      <div className="main-content">
        <div className="left-pane">
          <EditorPanel />
          {isPanelOpen('logs') && <LogPanel />}
          {isPanelOpen('plots') && <PlotPanel />}
        </div>
        <div className="center-pane">
          <SimulatorView />
          <StatusBar />
        </div>
        <SidePanel />
      </div>
    </div>
  )
}

export default App