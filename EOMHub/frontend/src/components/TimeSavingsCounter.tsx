import { memo, useMemo } from 'react'

interface TimeSavings {
  totalSeconds: number;
  totalSecondsMin?: number;
  totalSecondsMax?: number;
  executed: Record<string, number>;
  history: Array<{
    tool_id: string;
    minutes: number;
    minutes_min?: number;
    minutes_max?: number;
    timestamp: number;
    time: string;
  }>;
}

interface TimeSavingsCounterProps {
  savings: TimeSavings;
  onReset: () => void;
}

function formatTime(totalMinutes: number): { hours: number; minutes: number } {
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return { hours, minutes }
}

const TimeSavingsCounter = memo(function TimeSavingsCounter({
  savings,
  onReset,
}: TimeSavingsCounterProps) {
  const totalSecondsMin = savings.totalSecondsMin ?? savings.totalSeconds
  const totalSecondsMax = savings.totalSecondsMax ?? savings.totalSeconds

  const totalMinutes = Math.floor(savings.totalSeconds / 60)
  const totalMinutesMin = Math.floor(totalSecondsMin / 60)
  const totalMinutesMax = Math.floor(totalSecondsMax / 60)

  const { hours, minutes } = useMemo(() => formatTime(totalMinutes), [totalMinutes])
  const { hours: minHours, minutes: minMinutes } = useMemo(() => formatTime(totalMinutesMin), [totalMinutesMin])
  const { hours: maxHours, minutes: maxMinutes } = useMemo(() => formatTime(totalMinutesMax), [totalMinutesMax])
  const showRange = totalMinutesMin !== totalMinutesMax

  const totalExecutions = Object.values(savings.executed).reduce((sum, count) => sum + count, 0)

  return (
    <div className="time-savings-counter">
      <div className="savings-header">
        <span className="savings-label">Время сэкономлено</span>
        <button
          type="button"
          className="reset-button"
          onClick={onReset}
          title="Сбросить статистику"
          aria-label="Сбросить статистику"
        >
          ↻
        </button>
      </div>

      <div className="savings-display">
        <div className="time-block">
          <span className="time-value">{hours}</span>
          <span className="time-unit">ч</span>
        </div>
        <span className="time-separator">:</span>
        <div className="time-block">
          <span className="time-value">{minutes.toString().padStart(2, '0')}</span>
          <span className="time-unit">мин</span>
        </div>
      </div>

      {showRange && (
        <div className="savings-range">
          Диапазон: {minHours}ч {minMinutes.toString().padStart(2, '0')}мин – {maxHours}ч {maxMinutes
            .toString()
            .padStart(2, '0')}мин
        </div>
      )}

      <div className="savings-stats">
        <span className="stat">
          <span className="stat-value">{totalExecutions}</span>
          <span className="stat-label">операций</span>
        </span>
      </div>

      {savings.history.length > 0 && (
        <div className="recent-activity">
          <span className="activity-label">Последнее:</span>
          <span className="activity-time">
            {savings.history[savings.history.length - 1]?.time}
          </span>
        </div>
      )}
    </div>
  )
})

export default TimeSavingsCounter
