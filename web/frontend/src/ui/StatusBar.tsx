import { useSimulatorStore } from '@/stores/simulatorStore'

export function StatusBar() {
  const { simTime, running, states, collisions, config } = useSimulatorStore()

  const robotCount = Object.keys(states).length
  const collisionCount = Object.values(collisions).filter(c => c).length

  return (
    <div className="status-bar">
      <div className="status-item">
        <span className="label">Time:</span>
        <span className="value">{simTime.toFixed(2)}s</span>
      </div>
      <div className="status-item">
        <span className="label">Robots:</span>
        <span className="value">{robotCount}</span>
      </div>
      <div className="status-item">
        <span className="label">Collisions:</span>
        <span className={collisionCount > 0 ? 'value warning' : 'value'}>
          {collisionCount}
        </span>
      </div>
      <div className="status-item">
        <span className="label">Mode:</span>
        <span className="value">{config.robot?.type || 'differential'}</span>
      </div>
      <div className="status-item">
        <span className="label">FPS:</span>
        <span className="value fps">60</span>
      </div>
      <div className={`status-item status-${running ? 'running' : 'paused'}`}>
        {running ? '🟢 Running' : '🔴 Paused'}
      </div>
    </div>
  )
}