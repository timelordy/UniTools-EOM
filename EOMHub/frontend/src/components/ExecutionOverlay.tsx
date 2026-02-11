import React, { useEffect, useMemo, useRef } from 'react'

type JobStatus = 'idle' | 'pending' | 'running' | 'completed' | 'error' | 'cancelled'

interface UxErrorInfo {
  code: string
  title: string
  message: string
  nextAction?: string
  technicalMessage?: string
  canRetry: boolean
}

interface ExecutionOverlayProps {
  visible: boolean
  status: JobStatus
  toolId?: string | null
  toolName?: string | null
  jobId?: string | null
  jobDisplayName?: string | null
  message?: string
  queueLabel?: string | null
  stats?: {
    total?: number
    processed?: number
    skipped?: number
    errors?: number
  } | null
  summary?: Record<string, unknown> | null
  uxError?: UxErrorInfo | null
  canCancel: boolean
  onCancel?: () => void
}

const statusHintMap: Record<JobStatus, string> = {
  idle: 'Готово к запуску',
  pending: 'Запрос отправлен в Revit…',
  running: 'Скрипт выполняется…',
  completed: 'Запуск завершён',
  error: 'Возникла ошибка',
  cancelled: 'Выполнение отменено',
}

const toNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return Math.round(value)
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return Math.round(parsed)
  }
  return null
}

const resolveEntityLabel = (toolId?: string | null, toolName?: string | null): string => {
  const id = (toolId || '').toLowerCase()
  const name = (toolName || '').toLowerCase()
  const key = `${id} ${name}`

  if (key.includes('light') || key.includes('свет')) return 'светильников'
  if (
    key.includes('socket')
    || key.includes('розет')
    || key.includes('kitchen_block')
    || key.includes('wet_zones')
    || key.includes('low_voltage')
    || key.includes('outlet')
  ) {
    return 'розеток'
  }
  if (key.includes('switch') || key.includes('выключ')) return 'выключателей'
  if (key.includes('panel_door') || key.includes('щит') || key.includes('panel')) return 'щитов'
  return 'элементов'
}

const ExecutionOverlay: React.FC<ExecutionOverlayProps> = ({
  visible,
  status,
  toolId,
  toolName,
  jobId,
  jobDisplayName,
  message,
  queueLabel,
  stats,
  summary,
  uxError,
  canCancel,
  onCancel,
}) => {
  const cancelButtonRef = useRef<HTMLButtonElement | null>(null)

  const safeStats = stats || undefined
  const total = safeStats?.total ?? 0
  const processed = safeStats?.processed ?? 0
  const placedFromSummary = toNumber(summary?.placed)
  const placedCount = placedFromSummary ?? (processed > 0 ? processed : null)
  const placedEntity = useMemo(() => resolveEntityLabel(toolId, toolName), [toolId, toolName])

  const percent = total > 0 ? Math.min(100, Math.round((processed / Math.max(total, 1)) * 100)) : null
  const isRunning = status === 'pending' || status === 'running'
  const isCompleted = status === 'completed'
  const isError = status === 'error' && !!uxError

  useEffect(() => {
    if (!visible || !isRunning || !canCancel || !onCancel) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      event.preventDefault()
      onCancel()
    }

    window.addEventListener('keydown', handleKeyDown, true)
    cancelButtonRef.current?.focus()
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [visible, isRunning, canCancel, onCancel])

  const fallbackMessage = statusHintMap[status] || statusHintMap.idle

  if (!visible) return null

  const displayMessage = message?.trim() ? message : fallbackMessage
  const completionMessage = placedCount != null
    ? `Размещено ${placedCount} ${placedEntity}`
    : 'Выполнение завершено'

  return (
    <div className="apply-progress-overlay" role="dialog" aria-modal="true" aria-live="assertive">
      <div className="apply-progress-dialog">
        <div className="apply-progress-header">
          <div className="apply-progress-title">
            <div className="apply-progress-tool">{toolName || 'Инструмент'}</div>
          </div>
          {isRunning ? <div className="apply-progress-spinner" aria-hidden="true" /> : null}
          {isCompleted ? <div className="apply-progress-check" aria-hidden="true">✓</div> : null}
        </div>

        {isRunning && queueLabel ? <div className="apply-progress-queue">{queueLabel}</div> : null}

        {isRunning ? (
          <div className="apply-progress-task">
            <div className="apply-progress-message" title={jobId || undefined}>{displayMessage || jobDisplayName || jobId || 'Выполнение...'}</div>
          </div>
        ) : null}

        {isRunning && percent != null ? (
          <div className="apply-progress-bar-container">
            <div className="apply-progress-bar">
              <div className="apply-progress-bar-fill" style={{ width: `${percent}%` }}>
                <div className="progress-bar-shine" />
              </div>
            </div>
            <div className="apply-progress-percentage">
              <span>{total > 0 ? `${processed} из ${total}` : fallbackMessage}</span>
              <span>{percent}%</span>
            </div>
          </div>
        ) : null}

        {isCompleted ? (
          <div className="apply-progress-complete">
            <div className="apply-progress-complete-title">Готово</div>
            <div className="apply-progress-complete-text">{completionMessage}</div>
          </div>
        ) : null}

        {isError ? (
          <div className="apply-progress-complete" role="alert" aria-live="assertive">
            <div className="apply-progress-complete-title">{uxError?.title}</div>
            <div className="apply-progress-complete-text">{uxError?.message}</div>
            {uxError?.nextAction ? (
              <div className="cancel-hint" style={{ textAlign: 'left', marginTop: 6 }}>{uxError.nextAction}</div>
            ) : null}
          </div>
        ) : null}

        <div className="apply-progress-actions">
          {isRunning && canCancel ? (
            <button
              ref={cancelButtonRef}
              type="button"
              className="btn-cancel-progress"
              onClick={onCancel}
            >
              Отменить (Esc)
            </button>
          ) : isRunning ? (
            <div className="cancel-hint">{fallbackMessage}</div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default ExecutionOverlay
