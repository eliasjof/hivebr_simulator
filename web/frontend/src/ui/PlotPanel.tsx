import { useEffect, useRef } from 'react'
import * as uPlot from 'uplot'
import 'uplot/dist/uPlot.min.css'
import { useSimulatorStore } from '@/stores/simulatorStore'

interface TelemetryData {
  time: Float64Array
  x: Float64Array
  y: Float64Array
  theta: Float64Array
  v: Float64Array
  omega: Float64Array
  [key: string]: Float64Array
}

function createEmptyData(): TelemetryData {
  return {
    time: new Float64Array(0),
    x: new Float64Array(0),
    y: new Float64Array(0),
    theta: new Float64Array(0),
    v: new Float64Array(0),
    omega: new Float64Array(0),
  }
}

function pushData(data: TelemetryData, values: number[]): void {
  const keys: readonly string[] = ['time', 'x', 'y', 'theta', 'v', 'omega']
  for (let i = 0; i < keys.length; i++) {
    const key = keys[i]
    const arr = data[key]
    const newArr = new Float64Array(arr.length + 1)
    newArr.set(arr)
    newArr[arr.length] = values[i]
    data[key] = newArr
  }
}

function shiftData(data: TelemetryData): void {
  const keys: readonly string[] = ['time', 'x', 'y', 'theta', 'v', 'omega']
  for (let i = 0; i < keys.length; i++) {
    const key = keys[i]
    data[key] = data[key].slice(1)
  }
}

export function PlotPanel() {
  const { states, selectedRobot } = useSimulatorStore()
  const containerRef = useRef<HTMLDivElement>(null)
  const dataRef = useRef<TelemetryData>(createEmptyData())

  useEffect(() => {
    if (!containerRef.current) return

    const robotIds = Object.keys(states).map(Number).sort((a, b) => a - b)
    if (robotIds.length === 0) return

    // Create uPlot instance
    const data = [
      dataRef.current.time,
      dataRef.current.x,
      dataRef.current.y,
      dataRef.current.theta,
      dataRef.current.v,
      dataRef.current.omega,
    ]

    const plot = new uPlot({
      title: 'Robot Telemetry',
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      series: [
        { label: 'Time', value: (_u: any, i: number) => data[0][i] },
        { 
          label: 'X (m)', 
          value: (_u: any, i: number) => data[1][i], 
          stroke: '#1e90ff',
          width: 2,
        },
        { 
          label: 'Y (m)', 
          value: (_u: any, i: number) => data[2][i], 
          stroke: '#dc143c',
          width: 2,
        },
        { 
          label: 'θ (rad)', 
          value: (_u: any, i: number) => data[3][i], 
          stroke: '#32cd32',
          width: 1,
          dash: [4, 4],
        },
        { 
          label: 'v (m/s)', 
          value: (_u: any, i: number) => data[4][i], 
          stroke: '#ffa500',
          width: 1,
        },
        { 
          label: 'ω (rad/s)', 
          value: (_u: any, i: number) => data[5][i], 
          stroke: '#9400d3',
          width: 1,
        },
      ],
      axes: [
        { label: 'Time (s)' },
        { label: 'Value' },
      ],
      scales: {
        x: { time: false },
      },
      cursor: { focus: { prox: 10 } },
      legend: { show: true, live: true },
    }, data, containerRef.current)

    // Update data periodically
    const interval = setInterval(() => {
      const currentStates = useSimulatorStore.getState().states
      const robotIds = Object.keys(currentStates).map(Number).sort((a, b) => a - b)
      
      if (robotIds.length === 0) return

      // For simplicity, plot the first robot or selected robot
      const targetId = selectedRobot !== undefined && currentStates[selectedRobot] 
        ? selectedRobot 
        : robotIds[0]
      
      const state = currentStates[targetId]
      if (!state) return

      const t = useSimulatorStore.getState().simTime

      pushData(dataRef.current, [t, state.x, state.y, state.theta, state.v, state.omega])

      // Trim old data
      if (dataRef.current.time.length > 500) {
        shiftData(dataRef.current)
      }

      // Update plot data
      const data = [
        dataRef.current.time,
        dataRef.current.x,
        dataRef.current.y,
        dataRef.current.theta,
        dataRef.current.v,
        dataRef.current.omega,
      ]
      plot.setData(data)
    }, 100)

    return () => {
      clearInterval(interval)
      plot.destroy()
    }
  }, [states, selectedRobot])

  return (
    <div className="plot-panel" ref={containerRef}>
      <div className="panel-header">
        <h4>Telemetry</h4>
      </div>
    </div>
  )
}