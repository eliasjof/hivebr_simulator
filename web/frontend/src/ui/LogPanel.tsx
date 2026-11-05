import { useSimulatorStore } from '@/stores/simulatorStore'

export function LogPanel() {
  const { logs, clearLogs } = useSimulatorStore()

  return (
    <div className="log-panel">
      <div className="panel-header">
        <h4>Logs</h4>
        <button className="btn btn-sm btn-secondary" onClick={clearLogs}>Clear</button>
      </div>
      <div className="log-container">
        {logs.length === 0 ? (
          <p className="empty-state">No logs yet</p>
        ) : (
          <div className="log-list">
            {logs.slice(-100).map(log => (
              <div key={log.id} className={`log-entry ${log.level}`}>
                <span className="log-time">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className="log-level">{log.level.toUpperCase()}</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}