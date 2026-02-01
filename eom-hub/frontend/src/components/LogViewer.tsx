import React, { useRef, useEffect } from "react"
import { LogEntry } from "../types"

interface LogViewerProps {
  logs: LogEntry[]
}

export const LogViewer: React.FC<LogViewerProps> = ({ logs }) => {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [logs])

  if (!logs || logs.length === 0) {
    return (
      <div className="log-viewer-empty" style={{ padding: '20px', textAlign: 'center', color: 'var(--text-secondary)', background: '#1e1e1e', borderRadius: '4px' }}>
        No logs available
      </div>
    )
  }

  return (
    <div 
      ref={containerRef}
      className="log-viewer" 
      style={{ 
        maxHeight: '400px', 
        overflowY: 'auto', 
        background: '#1e1e1e', 
        padding: '12px', 
        borderRadius: '4px',
        fontFamily: 'monospace',
        fontSize: '13px',
        lineHeight: '1.5'
      }}
    >
      {logs.map((log) => (
        <div 
          key={log.id} 
          className={`log-line log-${log.status}`}
          style={{
            color: log.status === 'error' ? '#ff6b6b' : 
                   log.status === 'warning' ? '#fcc419' : 
                   log.status === 'success' ? '#51cf66' : '#e9ecef',
            marginBottom: '4px',
            borderBottom: '1px solid #333',
            paddingBottom: '2px'
          }}
        >
          <span style={{ opacity: 0.7, marginRight: '8px', fontSize: '11px' }}>[{log.status.toUpperCase()}]</span>
          {log.message}
        </div>
      ))}
    </div>
  )
}
