import React from "react"
import { JobStats } from "../types"

interface ResultStatsProps {
  stats: JobStats
}

export const ResultStats: React.FC<ResultStatsProps> = ({ stats }) => {
  return (
    <div className="stats-container" style={{ display: 'flex', gap: '16px', padding: '16px', background: 'var(--surface-hover)', borderRadius: '8px', marginBottom: '16px' }}>
      <div className="stat-item" style={{ flex: 1, textAlign: 'center' }}>
        <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{stats.total}</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Total</div>
      </div>
      <div className="stat-item" style={{ flex: 1, textAlign: 'center' }}>
        <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--success)' }}>{stats.processed}</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Processed</div>
      </div>
      <div className="stat-item" style={{ flex: 1, textAlign: 'center' }}>
        <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--warning)' }}>{stats.skipped}</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Skipped</div>
      </div>
      <div className="stat-item" style={{ flex: 1, textAlign: 'center' }}>
        <div style={{ fontSize: '24px', fontWeight: 'bold', color: 'var(--error)' }}>{stats.errors}</div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Errors</div>
      </div>
    </div>
  )
}
