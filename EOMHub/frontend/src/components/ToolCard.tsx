import { memo } from 'react'

interface Tool {
  id: string;
  name: string;
  icon: string;
  description: string;
  category: string;
  time_saved: number;
  script_path: string;
}

interface ToolCardProps {
  tool: Tool;
  isRunning: boolean;
  executionCount: number;
  onRun: () => void;
  disabled: boolean;
}

const isImageUrl = (icon: string): boolean => {
  return icon.startsWith('data:image/') || 
         icon.startsWith('http://') || 
         icon.startsWith('https://') ||
         icon.startsWith('/');
}

const ToolCard = memo(function ToolCard({ 
  tool, 
  isRunning, 
  executionCount, 
  onRun, 
  disabled 
}: ToolCardProps) {
  return (
    <button
      className={`tool-card ${isRunning ? 'running' : ''} ${disabled ? 'disabled' : ''}`}
      onClick={onRun}
      disabled={disabled}
      title={tool.description}
    >
      <div className="tool-icon">
        {isRunning ? (
          <div className="spinner" />
        ) : isImageUrl(tool.icon) ? (
          <img 
            src={tool.icon} 
            alt={tool.name}
            style={{ width: '64px', height: '64px', objectFit: 'contain' }}
          />
        ) : (
          <span>{tool.icon}</span>
        )}
      </div>
      
      <div className="tool-info">
        <span className="tool-name">{tool.name}</span>
        {tool.description && tool.description !== '|' && (
          <span className="tool-desc">{tool.description}</span>
        )}
      </div>
      
      {executionCount > 0 && (
        <div className="tool-meta">
          <span className="execution-count" title="Выполнено раз">
            {executionCount}x
          </span>
        </div>
      )}
    </button>
  )
})

export default ToolCard
