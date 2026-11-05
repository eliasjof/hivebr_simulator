import { useSimulatorStore } from '@/stores/simulatorStore'
import { useUIStore } from '@/stores/uiStore'

export function SidePanel() {
  const { states, selectedRobot, setSelectedRobot, collisions, config } = useSimulatorStore()
  const { showLidar, toggleLidar, showPaths, togglePaths, showWaypoints, toggleWaypoints, showGrid, toggleGrid } = useUIStore()

  const robotIds = Object.keys(states).map(Number).sort((a, b) => a - b)

  return (
    <div className="side-panel">
      <div className="panel-section">
        <h4>Robots</h4>
        <div className="robot-list">
          {robotIds.map(id => (
            <button
              key={id}
              className={`robot-btn ${selectedRobot === id ? 'selected' : ''} ${collisions[id] ? 'colliding' : ''}`}
              onClick={() => setSelectedRobot(id)}
            >
              <span className="robot-id">B-Bot {id}</span>
              <span className="robot-type">{states[id]?.type || 'diff'}</span>
              <span className={`robot-status ${collisions[id] ? 'collision' : 'ok'}`}>
                {collisions[id] ? '💥' : '✓'}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="panel-section">
        <h4>Selected Robot</h4>
        {selectedRobot !== undefined && states[selectedRobot] ? (
          <div className="robot-details">
            <div className="detail-row">
              <span>Position:</span>
              <span>{states[selectedRobot].x.toFixed(2)}, {states[selectedRobot].y.toFixed(2)}</span>
            </div>
            <div className="detail-row">
              <span>Heading:</span>
              <span>{(states[selectedRobot].theta * 180 / Math.PI).toFixed(1)}°</span>
            </div>
            <div className="detail-row">
              <span>Velocity:</span>
              <span>v={states[selectedRobot].v.toFixed(2)}, ω={states[selectedRobot].omega.toFixed(2)}</span>
            </div>
            <div className="detail-row">
              <span>Battery:</span>
              <span>{states[selectedRobot].battery.toFixed(1)}%</span>
            </div>
            {states[selectedRobot].goal && (
              <div className="detail-row">
                <span>Goal:</span>
                <span>{states[selectedRobot].goal![0].toFixed(2)}, {states[selectedRobot].goal![1].toFixed(2)}</span>
              </div>
            )}
          </div>
        ) : (
          <p className="empty-state">Select a robot</p>
        )}
      </div>

      <div className="panel-section">
        <h4>Visualization</h4>
        <label className="checkbox">
          <input type="checkbox" checked={showGrid} onChange={toggleGrid} />
          <span>Grid</span>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={showLidar} onChange={toggleLidar} />
          <span>LiDAR</span>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={showPaths} onChange={togglePaths} />
          <span>Paths</span>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={showWaypoints} onChange={toggleWaypoints} />
          <span>Waypoints</span>
        </label>
      </div>

      <div className="panel-section">
        <h4>World Config</h4>
        <div className="config-item">
          <label>World Size</label>
          <input 
            type="number" 
            value={config.world?.width} 
            onChange={(e) => {
              const newConfig = { ...config, world: { ...config.world, width: Number(e.target.value) } }
              useSimulatorStore.getState().setConfig(newConfig)
            }} 
          />
          <span>×</span>
          <input 
            type="number" 
            value={config.world?.height} 
            onChange={(e) => {
              const newConfig = { ...config, world: { ...config.world, height: Number(e.target.value) } }
              useSimulatorStore.getState().setConfig(newConfig)
            }} 
          />
        </div>
        <div className="config-item">
          <label>Robot Type</label>
          <select 
            value={config.robot?.type} 
            onChange={(e) => {
              const newConfig = { ...config, robot: { ...config.robot, type: e.target.value } }
              useSimulatorStore.getState().setConfig(newConfig)
            }}
          >
            <option value="differential">Differential</option>
            <option value="holonomic">Holonomic</option>
            <option value="ackermann">Ackermann</option>
            <option value="boat">Boat</option>
            <option value="hexagonal_holonomic">Hex Holonomic</option>
            <option value="line_follower">Line Follower</option>
          </select>
        </div>
      </div>
    </div>
  )
}