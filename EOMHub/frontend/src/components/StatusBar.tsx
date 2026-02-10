import { memo } from 'react'

interface RevitStatus {
  connected: boolean;
  document?: string;
  documentPath?: string;
  revitVersion?: string;
  sessionId?: string;
}

interface StatusBarProps {
  status: RevitStatus;
}

const StatusBar = memo(function StatusBar({ status }: StatusBarProps) {
  return (
    <div className={`status-bar ${status.connected ? 'connected' : 'disconnected'}`}>
      <div className="status-indicator">
        <span className="status-dot" />
        <span className="status-text">
          {status.connected ? 'Подключено' : 'Нет подключения'}
        </span>
      </div>

      {status.connected && status.document && (
        <div className="document-info">
          <span className="document-name" title={status.documentPath}>
            {status.document}
          </span>
          {status.revitVersion && (
            <span className="revit-version">
              Revit {status.revitVersion}
            </span>
          )}
        </div>
      )}
    </div>
  )
})

export default StatusBar
