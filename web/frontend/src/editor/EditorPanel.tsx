import { useEffect, useRef, useState } from 'react'
import * as monaco from 'monaco-editor'
import { useSimulatorStore } from '@/stores/simulatorStore'

const HIVEBR_TYPES = `
declare module "hivebr" {
  export class HiveBrAgent {
    constructor(robot_id?: number, config?: any, params?: any);
    setup(): void;
    loop(state: RobotState, neighbors: Record<number, RobotState>): Command | [number, number];
    reset(): void;
    readonly cfg: any;
    readonly params: any;
    readonly id: number;
  }
  
  export class SwarmController {
    setup(): void;
    loop(states: Record<number, RobotState>): Record<number, Command | [number, number]>;
    reset(): void;
  }
  
  export class SwarmExperiment {
    constructor(options: { robots: number | any[]; backend?: string; config?: any; dt?: number });
    assign_agent(options: { robot_id?: number; robot_ids?: number[]; agent_class: any; params?: any }): this;
    set_controller(controller: SwarmController): this;
    assign_route(robot_id: number, waypoints: number[][]): this;
    run(): void;
    step(): void;
    reset(): void;
    save_log(path: string): void;
    plot_log(): void;
    print_collisions(): void;
  }
  
  export interface RobotState {
    id: number;
    x: number; y: number; theta: number;
    v: number; omega: number;
    type: string;
    radius: number;
    battery: number;
    goal: [number, number] | [number, number, number] | null;
  }
  
  export interface Command {
    v?: number; omega?: number;
    vx?: number; vy?: number;
    speed?: number; steer?: number;
  }
  
  export function load_config(path: string): any;
}

interface RobotState {
  id: number;
  x: number; y: number; theta: number;
  v: number; omega: number;
  type: string;
  radius: number;
  battery: number;
  goal: [number, number] | [number, number, number] | null;
}

interface Command {
  v?: number; omega?: number;
  vx?: number; vy?: number;
  speed?: number; steer?: number;
}
`

export function EditorPanel() {
  const editorRef = useRef<HTMLDivElement>(null)
  const editorInstanceRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null)
  const { userCode, setUserCode, worker } = useSimulatorStore()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!editorRef.current || editorInstanceRef.current) return

    // Register TypeScript definitions
    monaco.languages.typescript.javascriptDefaults.addExtraLib(HIVEBR_TYPES, 'hivebr.d.ts')

    const newEditor = monaco.editor.create(editorRef.current, {
      value: userCode,
      language: 'python',
      theme: 'vs-dark',
      automaticLayout: true,
      minimap: { enabled: false },
      fontSize: 13,
      lineNumbers: 'on',
      scrollBeyondLastLine: false,
      tabSize: 4,
      insertSpaces: true,
      wordWrap: 'on',
      bracketPairColorization: { enabled: true },
      guides: { bracketPairs: true },
    })

    newEditor.onDidChangeModelContent(() => {
      const code = newEditor.getValue()
      setUserCode(code)
      // Validate syntax
      validateCode(code)
    })

    editorInstanceRef.current = newEditor

    return () => {
      newEditor.dispose()
    }
  }, [userCode, setUserCode])

  const validateCode = (_code: string) => {
    try {
      // Basic Python syntax validation
      // In production, you'd use a proper Python parser
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Syntax error')
    }
  }

  const handleRun = async () => {
    if (!worker) return
    setError(null)
    try {
      await worker.init(
        useSimulatorStore.getState().config,
        editorInstanceRef.current?.getValue() || userCode
      )
      worker.step(0.03) // First step to initialize
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start simulation')
    }
  }

  const handleReset = async () => {
    if (!worker) return
    try {
      await worker.reset()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reset failed')
    }
  }

  return (
    <div className="editor-panel">
      <div className="panel-header">
        <h3>Editor</h3>
        <div className="panel-actions">
          <button className="btn btn-primary" onClick={handleRun} title="Run (Ctrl+Enter)">
            ▶ Run
          </button>
          <button className="btn btn-secondary" onClick={handleReset} title="Reset">
            ↻ Reset
          </button>
        </div>
      </div>
      {error && <div className="editor-error">{error}</div>}
      <div className="editor-container" ref={editorRef} />
    </div>
  )
}