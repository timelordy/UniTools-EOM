import React from 'react'
import './TimeSavings.css'

export interface TimeSavingsData {
    totalSeconds: number
    executed: Record<string, number>
    history: Array<{
        tool_id: string
        minutes: number
        timestamp: number
        time: string
    }>
}

interface TimeSavingsProps {
    data: TimeSavingsData
    isLoading?: boolean
}

export const TimeSavings: React.FC<TimeSavingsProps> = ({ data, isLoading }) => {
    const sec = data.totalSeconds || 0
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    const s = Math.floor(sec % 60)

    // Calculate average
    const count = Object.values(data.executed || {}).reduce((a, b) => a + b, 0)
    const avg = count > 0 ? Math.round((sec / 60) / count) : 0

    return (
        <div className="time-savings-dashboard">
            <div className="dashboard-grid">
                <div className="total-counter">
                    <div className="total-label">Сэкономлено времени</div>
                    <div className="total-time">
                        {h}:{m.toString().padStart(2, '0')}:{s.toString().padStart(2, '0')}
                    </div>
                    <div className="total-breakdown">
                        {h} ч {m} мин
                    </div>
                </div>

                <div className="stats-panel">
                    <div className="stat-card">
                        <div className="stat-icon">📊</div>
                        <div className="stat-info">
                            <div className="stat-value">{count}</div>
                            <div className="stat-label">Задач выполнено</div>
                        </div>
                    </div>
                    <div className="stat-card">
                        <div className="stat-icon">⚡</div>
                        <div className="stat-info">
                            <div className="stat-value">{avg} м</div>
                            <div className="stat-label">В среднем на задачу</div>
                        </div>
                    </div>
                </div>
            </div>

            {data.history && data.history.length > 0 && (
                <div className="history-list">
                    {data.history.slice(0, 10).map((item, idx) => (
                        <div key={idx} className="history-item">
                            <span className="history-time">{item.time}</span>
                            <span className="history-tool">{item.tool_id}</span>
                            <span className="history-val">+{item.minutes} м</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
