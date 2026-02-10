import { useState, useEffect, useCallback, useMemo, useRef, useId } from 'react'
import ToolCard from './components/ToolCard'
import TimeSavingsCounter from './components/TimeSavingsCounter'
import ExecutionOverlay from './components/ExecutionOverlay'
import StatusBar from './components/StatusBar'

// Eel interface
declare global {
  interface Window {
    eel: {
      get_tools_config(): () => Promise<ToolsConfig>;
      get_revit_status(): () => Promise<RevitStatus>;
      run_tool(toolId: string, jobId?: string): () => Promise<RunResult>;
      get_job_result(jobId: string): () => Promise<JobResult | null>;
      get_time_savings(): () => Promise<TimeSavings>;
      add_time_saving(toolId: string, minutes: number | { min: number; max: number }): () => Promise<TimeSavings>;
      reset_time_savings(): () => Promise<TimeSavings>;
    };
  }
}

interface Tool {
  id: string;
  name: string;
  icon: string;
  description: string;
  category: string;
  time_saved: number; // fallback: minutes per run
  script_path: string;
}

interface Category {
  id: string;
  name: string;
  icon: string;
  order: number;
}

interface ToolsConfig {
  tools: Record<string, Tool>;
  categories: Record<string, Category>;
  dangerous_tools?: string[];
  warning_messages?: Record<string, string>;
}

interface RevitStatus {
  connected: boolean;
  document?: string;
  documentPath?: string;
  revitVersion?: string;
  sessionId?: string;
}

interface RunResult {
  success: boolean;
  job_id?: string;
  tool_id?: string;
  message?: string;
  error?: string;
}

type JobStatus = 'idle' | 'pending' | 'running' | 'completed' | 'error' | 'cancelled'

interface JobStats {
  total: number;
  processed: number;
  skipped: number;
  errors: number;
}

interface JobDetail {
  id: string;
  status: string;
  message: string;
  number?: string;
  level?: string;
}

interface JobResult {
  job_id: string;
  tool_id: string;
  status?: string;
  message?: string;
  error?: string;
  executionTime?: number;
  stats?: JobStats;
  details?: JobDetail[];
  summary?: Record<string, unknown>;
}

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

type ConfirmVariant = 'default' | 'danger'

interface ConfirmDialogState {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: ConfirmVariant
  defaultAction?: 'confirm' | 'cancel'
}

let eelBridgeFailed = false
const FORCE_REST_MODE = true
const EEL_CALL_TIMEOUT_MS = 1200
const SHOW_RESULT_PANEL = false

const hasEelBridge = () => {
  if (FORCE_REST_MODE) return false
  if (typeof window === 'undefined') return false
  return !eelBridgeFailed && !!window.eel
}

const withTimeout = async <T,>(promise: Promise<T>, timeoutMs: number): Promise<T> => {
  return new Promise<T>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      reject(new Error(`Eel bridge timeout after ${timeoutMs}ms`))
    }, timeoutMs)

    promise
      .then((value) => {
        window.clearTimeout(timer)
        resolve(value)
      })
      .catch((error) => {
        window.clearTimeout(timer)
        reject(error)
      })
  })
}

const callEel = async <T,>(invoke: () => Promise<T>): Promise<T | null> => {
  if (!hasEelBridge()) return null
  try {
    return await withTimeout(invoke(), EEL_CALL_TIMEOUT_MS)
  } catch (error) {
    eelBridgeFailed = true
    console.warn('Eel bridge call failed, switching to REST fallback:', error)
    return null
  }
}

const fetchApi = async <T,>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(path, init)
  const payload = (await response.json()) as T & { error?: string }
  if (!response.ok) {
    throw new Error(payload?.error || `HTTP ${response.status}`)
  }
  return payload as T
}

const getToolsConfig = async (): Promise<ToolsConfig> => {
  const eelResult = await callEel(() => window.eel.get_tools_config()())
  if (eelResult) return eelResult
  return fetchApi<ToolsConfig>('/api/tools-config')
}

const getRevitStatus = async (): Promise<RevitStatus> => {
  const eelResult = await callEel(() => window.eel.get_revit_status()())
  if (eelResult) return eelResult
  return fetchApi<RevitStatus>('/api/revit-status')
}

const getTimeSavings = async (): Promise<TimeSavings> => {
  const eelResult = await callEel(() => window.eel.get_time_savings()())
  if (eelResult) return eelResult
  return fetchApi<TimeSavings>('/api/time-savings')
}

const getJobResult = async (jobId: string): Promise<JobResult | null> => {
  const eelResult = await callEel(() => window.eel.get_job_result(jobId)())
  if (eelResult) return eelResult
  return fetchApi<JobResult | null>(`/api/job-result/${encodeURIComponent(jobId)}`)
}

const runTool = async (toolId: string, jobId?: string): Promise<RunResult> => {
  const eelResult = await callEel(() => window.eel.run_tool(toolId, jobId)())
  if (eelResult) return eelResult
  return fetchApi<RunResult>('/api/run-tool', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ toolId, jobId }),
  })
}

const resetTimeSavings = async (): Promise<TimeSavings> => {
  const eelResult = await callEel(() => window.eel.reset_time_savings()())
  if (eelResult) return eelResult
  return fetchApi<TimeSavings>('/api/reset-time-savings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
}

const addTimeSaving = async (
  toolId: string,
  minutes: number | { min: number; max: number },
): Promise<TimeSavings> => {
  const eelResult = await callEel(() => window.eel.add_time_saving(toolId, minutes)())
  if (eelResult) return eelResult
  return fetchApi<TimeSavings>('/api/add-time-saving', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ toolId, minutes }),
  })
}

function App() {
  const [config, setConfig] = useState<ToolsConfig | null>(null)
  const [status, setStatus] = useState<RevitStatus>({ connected: false })
  const [savings, setSavings] = useState<TimeSavings>({ totalSeconds: 0, executed: {}, history: [] })
  const configLoadedRef = useRef(false)
  const [, setRunningTool] = useState<string | null>(null)
  const [pendingJobIds, setPendingJobIds] = useState<string[]>([])
  const [jobMetaById, setJobMetaById] = useState<Record<string, { toolId: string; minutes: number }>>({})
  const [countedJobIds, setCountedJobIds] = useState<Record<string, true>>({})
  const [jobDisplayNameById, setJobDisplayNameById] = useState<Record<string, string>>({})
  const jobRunCountersRef = useRef<Record<string, number>>({})
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [showConnectionHelp, setShowConnectionHelp] = useState(false)
  const [lastTool, setLastTool] = useState<Tool | null>(null)
  const [lastJobId, setLastJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus>('idle')
  const [jobResult, setJobResult] = useState<JobResult | null>(null)
  const [jobMessage, setJobMessage] = useState<string>('')
  const [resultTab, setResultTab] = useState<'result' | 'logs'>('result')
  const [overlayJobId, setOverlayJobId] = useState<string | null>(null)
  const overlayHideTimerRef = useRef<number | null>(null)
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState | null>(null)
  const confirmResolveRef = useRef<((value: boolean) => void) | null>(null)

  const requestConfirm = useCallback((next: ConfirmDialogState) => {
    return new Promise<boolean>((resolve) => {
      confirmResolveRef.current = resolve
      setConfirmDialog(next)
    })
  }, [])

  const closeConfirm = useCallback((value: boolean) => {
    const resolve = confirmResolveRef.current
    confirmResolveRef.current = null
    setConfirmDialog(null)
    resolve?.(value)
  }, [])

  useEffect(() => {
    return () => {
      const resolve = confirmResolveRef.current
      confirmResolveRef.current = null
      resolve?.(false)
    }
  }, [])

  // Load config and status
  useEffect(() => {
    const loadData = async () => {
      try {
        const cfg = await getToolsConfig()
        setConfig(cfg)
        configLoadedRef.current = true

        const st = await getRevitStatus()
        setStatus(st)

        const sv = await getTimeSavings()
        setSavings(sv)
      } catch (e) {
        console.error('Failed to load data:', e)
      }
    }

    loadData()

    // Poll status every 5 seconds
    const interval = setInterval(async () => {
      try {
        if (!configLoadedRef.current) {
          const cfg = await getToolsConfig()
          setConfig(cfg)
          configLoadedRef.current = true

          const sv = await getTimeSavings()
          setSavings(sv)
        }

        const st = await getRevitStatus()
        setStatus(st)
      } catch {
        // ignore
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  // Poll all queued jobs so tools are independent.
  useEffect(() => {
    let stopped = false

    const poll = async () => {
      if (stopped) return

      const jobIds = Array.from(new Set([...(pendingJobIds || []), ...(lastJobId ? [lastJobId] : [])]))
      if (!jobIds.length) return

      try {
        const results = await Promise.all(
          jobIds.map(async (jobId) => {
            try {
              const res = await getJobResult(jobId)
              return { jobId, res }
            } catch (e) {
              return { jobId, res: { job_id: jobId, tool_id: '', status: 'error', error: (e as Error).message } as JobResult }
            }
          })
        )

        for (const { jobId, res } of results) {
          if (!res) continue

          const status = (res.status as JobStatus) || 'completed'
          const isTerminal = status === 'completed' || status === 'error' || status === 'cancelled'

          // Update main result panel for the last selected job.
          if (jobId === lastJobId) {
            setJobResult(res)
            setJobStatus(status)
            if (res.message) setJobMessage(res.message)
            else if (res.error) setJobMessage(res.error)

            if (isTerminal) {
              setRunningTool(null)
            }
          }

          // Count time savings ONLY after completion, once.
          if (status === 'completed' && !countedJobIds[jobId]) {
            const meta = jobMetaById[jobId]
            const summary =
              res.summary as
                | {
                    time_saved_minutes?: unknown
                    time_saved_minutes_min?: unknown
                    time_saved_minutes_max?: unknown
                  }
                | undefined

            const summaryAvg = summary && typeof summary.time_saved_minutes === 'number' ? summary.time_saved_minutes : null
            const summaryMin =
              summary && typeof summary.time_saved_minutes_min === 'number' ? summary.time_saved_minutes_min : null
            const summaryMax =
              summary && typeof summary.time_saved_minutes_max === 'number' ? summary.time_saved_minutes_max : null

            let minutesMin: number | null = summaryMin
            let minutesMax: number | null = summaryMax

            if (minutesMin == null && minutesMax == null && summaryAvg != null) {
              minutesMin = summaryAvg
              minutesMax = summaryAvg
            }

            if (minutesMin == null && minutesMax != null) minutesMin = minutesMax
            if (minutesMax == null && minutesMin != null) minutesMax = minutesMin

            let toolIdForSaving: string | null = meta?.toolId || res.tool_id || null

            // Fallback: treat tool.time_saved as per-run minutes.
            if ((minutesMin == null || minutesMax == null) && meta) {
              minutesMin = meta.minutes
              minutesMax = meta.minutes
            }

            if (minutesMin != null && minutesMax != null && minutesMax > 0 && toolIdForSaving) {
              try {
                const newSavings = await addTimeSaving(toolIdForSaving, { min: minutesMin, max: minutesMax })
                setSavings(newSavings)
              } catch {
                // ignore
              }
            }

            setCountedJobIds((prev) => ({ ...prev, [jobId]: true }))
          }

          if (isTerminal) {
            setPendingJobIds((prev) => prev.filter((x) => x !== jobId))
            setJobMetaById((prev) => {
              if (!prev[jobId]) return prev
              const next = { ...prev }
              delete next[jobId]
              return next
            })
          } else {
            setPendingJobIds((prev) => (prev.includes(jobId) ? prev : [...prev, jobId]))
          }
        }
      } catch {
        // ignore
      }
    }

    const timer = window.setInterval(() => {
      void poll()
    }, 500)
    void poll()

    return () => {
      stopped = true
      window.clearInterval(timer)
    }
  }, [pendingJobIds, lastJobId, countedJobIds, jobMetaById])

  const runningToolIds = useMemo(() => {
    const ids = new Set<string>()
    for (const jobId of pendingJobIds) {
      const meta = jobMetaById[jobId]
      if (meta?.toolId) ids.add(meta.toolId)
    }
    return ids
  }, [pendingJobIds, jobMetaById])

  const queueLabel = useMemo(() => {
    const queueSize = pendingJobIds.length
    if (queueSize <= 1) return null
    const others = queueSize - 1
    return `В очереди: ${others}`
  }, [pendingJobIds])

  const friendlyJobName = useMemo(() => {
    if (!lastJobId) return null
    return jobDisplayNameById[lastJobId] || null
  }, [lastJobId, jobDisplayNameById])

  useEffect(() => {
    if (overlayHideTimerRef.current != null) {
      window.clearTimeout(overlayHideTimerRef.current)
      overlayHideTimerRef.current = null
    }

    if (!lastTool || !lastJobId) {
      setOverlayJobId(null)
      return
    }

    if (jobStatus === 'pending' || jobStatus === 'running') {
      setOverlayJobId(lastJobId)
      return
    }

    if (jobStatus === 'completed') {
      setOverlayJobId(lastJobId)
      overlayHideTimerRef.current = window.setTimeout(() => {
        setOverlayJobId((current) => (current === lastJobId ? null : current))
        overlayHideTimerRef.current = null
      }, 1300)
      return
    }

    // Default: don't show overlay for other states.
    setOverlayJobId(null)
  }, [jobStatus, lastJobId, lastTool])

  const overlayVisible = Boolean(lastTool && overlayJobId && overlayJobId === lastJobId)

  useEffect(() => {
    if (status.connected) {
      setShowConnectionHelp(false)
    }
  }, [status.connected])

  const handleRunTool = useCallback(async (tool: Tool) => {
    if (!status.connected) {
      setLastTool(tool)
      setJobStatus('error')
      setJobMessage('Revit не готов. Откройте проект и нажмите кнопку Hub в Revit, затем повторите.')
      setShowConnectionHelp(true)
      setResultTab('result')
      return
    }

    // Check for dangerous tools
    if (config?.dangerous_tools?.includes(tool.id)) {
      const msg = config.warning_messages?.[tool.id] || config.warning_messages?.default || 'Продолжить?'
      const ok = await requestConfirm({
        title: 'Требуется подтверждение',
        message: msg,
        confirmLabel: 'Продолжить',
        cancelLabel: 'Отмена',
        variant: 'danger',
        defaultAction: 'cancel',
      })
      if (!ok) return
    }

    // Запуск не блокирует другие инструменты: можно ставить в очередь несколько задач.
    setRunningTool(tool.id)
    setLastTool(tool)
    setLastJobId(null) // Сбрасываем старый job_id
    setJobResult(null)
    setJobMessage('')
    setJobStatus('pending')
    setResultTab('result')

    try {
      const result = await runTool(tool.id)

      if (result.success) {
        setLastJobId(result.job_id || null)
        setJobMessage(result.message || 'Команда отправлена в Revit')
        const jobId = result.job_id
        if (jobId) {
          setPendingJobIds((prev) => (prev.includes(jobId) ? prev : [...prev, jobId]))
          setJobMetaById((prev) => ({ ...prev, [jobId]: { toolId: tool.id, minutes: tool.time_saved } }))
          const baseName = tool.name?.trim() || 'Задача'
          const prevCount = jobRunCountersRef.current[tool.id] || 0
          const nextCount = prevCount + 1
          jobRunCountersRef.current = { ...jobRunCountersRef.current, [tool.id]: nextCount }
          const computedFriendlyName = `${baseName}_${nextCount}`
          setJobDisplayNameById((prev) => ({ ...prev, [jobId]: computedFriendlyName }))
        }
      } else {
        setLastJobId(null)
        setJobStatus('error')
        setJobMessage(result.error || 'Не удалось отправить команду в Revit')
        setRunningTool(null)
      }
    } catch (e) {
      console.error('Failed to run tool:', e)
      setLastJobId(null)
      setJobStatus('error')
      setJobMessage((e as Error).message || 'Не удалось отправить команду в Revit')
      setRunningTool(null)
    }
  }, [config, requestConfirm, status.connected])

  const handleResetSavings = useCallback(async () => {
    const ok = await requestConfirm({
      title: 'Сбросить прогресс?',
      message: 'Сбросить всю статистику экономии времени? Данные нельзя восстановить.',
      confirmLabel: 'Сбросить',
      cancelLabel: 'Отмена',
      variant: 'danger',
      defaultAction: 'cancel',
    })
    if (!ok) return

    try {
      const newSavings = await resetTimeSavings()
      setSavings(newSavings)
    } catch (e) {
      console.error('Failed to reset savings:', e)
    }
  }, [requestConfirm])

  const handleCancel = useCallback(async () => {
    if (!jobStatus || jobStatus === 'completed' || jobStatus === 'error' || jobStatus === 'cancelled') return

    try {
      // Send cancel command with current job ID if available, or just generic cancel
      // Based on script.py logic, "run:cancel:jobId" is handled.
      // run_tool('cancel', lastJobId) -> "run:cancel:lastJobId"
      if (lastJobId) {
        await runTool('cancel', lastJobId)
      } else {
        await runTool('cancel')
      }
      setJobMessage('Запрос на отмену отправлен...')
    } catch (e) {
      console.error('Failed to cancel:', e)
    }
  }, [jobStatus, lastJobId])

  // Group tools by category
  const toolsByCategory = config ? Object.values(config.tools).reduce((acc, tool) => {
    if (!acc[tool.category]) acc[tool.category] = []
    acc[tool.category].push(tool)
    return acc
  }, {} as Record<string, Tool[]>) : {}

  // Sort categories by order
  const sortedCategories = config ? Object.values(config.categories).sort((a, b) => a.order - b.order) : []

  // Filter tools by active category
  const filteredCategories = activeCategory
    ? sortedCategories.filter(c => c.id === activeCategory)
    : sortedCategories

  const jobStatusLabel = useMemo(() => {
    switch (jobStatus) {
      case 'pending':
        return 'В очереди'
      case 'running':
        return 'Выполняется'
      case 'completed':
        return 'Готово'
      case 'error':
        return 'Ошибка'
      case 'cancelled':
        return 'Отменено'
      default:
        return 'Ожидание'
    }
  }, [jobStatus])

  const resolvedStats = useMemo(() => {
    if (jobResult?.stats) return jobResult.stats
    const details = jobResult?.details || []
    if (!details.length) return null

    const processed = details.filter(d => d.status === 'success').length
    const skipped = details.filter(d => d.status === 'skipped').length
    const errors = details.filter(d => d.status === 'error').length
    return {
      total: details.length,
      processed,
      skipped,
      errors,
    }
  }, [jobResult])

  const hasLogs = Boolean(jobResult?.details && jobResult.details.length)

  return (
    <div className="app">
      <header className="hub-top-bar">
        <div className="hub-brand">
          <span className="hub-brand-title">UniTools</span>
          <span className="hub-brand-chip">EOM</span>
        </div>
        <StatusBar status={status} />
      </header>

      <main className="main">
        <TimeSavingsCounter
          savings={savings}
          onReset={handleResetSavings}
        />

        <div className="category-tabs">
          <button
            className={`tab ${!activeCategory ? 'active' : ''}`}
            onClick={() => setActiveCategory(null)}
          >
            Все
          </button>
          {sortedCategories.map(cat => (
            <button
              key={cat.id}
              className={`tab ${activeCategory === cat.id ? 'active' : ''}`}
              onClick={() => setActiveCategory(cat.id)}
            >
              {cat.icon} {cat.name}
            </button>
          ))}
        </div>

        {!status.connected && (
          <section className="connection-help-card" role="status" aria-live="polite">
            <h2 className="connection-help-title">Подключите Revit, чтобы запускать инструменты</h2>
            <p className="connection-help-text">Откройте проект в Revit и нажмите кнопку Hub на панели pyRevit.</p>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowConnectionHelp((prev) => !prev)}
            >
              {showConnectionHelp ? 'Скрыть инструкцию' : 'Как подключиться'}
            </button>
            {showConnectionHelp && (
              <ol className="connection-help-steps">
                <li>Откройте нужный проект в Revit.</li>
                <li>На вкладке pyRevit нажмите кнопку Hub.</li>
                <li>Дождитесь статуса «Подключено» и запустите инструмент.</li>
              </ol>
            )}
          </section>
        )}

        <div className="tools-container">
          {filteredCategories.map(category => (
            <section key={category.id} className="category-section">
              <h2 className="category-title">
                <span className="category-icon">{category.icon}</span>
                {category.name}
                <span className="category-count">{toolsByCategory[category.id]?.length || 0}</span>
              </h2>
              <div className="tools-grid">
                {toolsByCategory[category.id]?.map(tool => (
                  <ToolCard
                    key={tool.id}
                    tool={tool}
                    isRunning={runningToolIds.has(tool.id)}
                    executionCount={savings.executed[tool.id] || 0}
                    onRun={() => handleRunTool(tool)}
                    disabled={!status.connected}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

	    {SHOW_RESULT_PANEL && (
	      <section className="result-panel">
          <div className="result-header">
            <div className="result-title">
              <span>Результат запуска</span>
              {lastTool && <span className="result-tool">{lastTool.name}</span>}
            </div>
            <div className="result-header-actions">
              <div className={`result-status status-${jobStatus}`}>
                {jobStatusLabel}
              </div>
              {(jobStatus === 'running' || jobStatus === 'pending') && (
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={handleCancel}
                  title="Отменить выполнение"
                >
                  ОТМЕНА
                </button>
              )}
            </div>
          </div>

          {!lastJobId && (
            <div className="result-empty">
              Запустите инструмент, чтобы увидеть результат.
            </div>
          )}

          {lastJobId && (
            <>
              <div className="result-meta">
                <span className="result-meta-item" title={lastJobId || undefined}>Задача: {friendlyJobName || lastJobId}</span>
                {jobResult?.executionTime != null && (
                  <span className="result-meta-item" style={{ fontWeight: 'bold', color: '#4CAF50' }}>
                    ⏱ Время: {Math.round(jobResult.executionTime * 10) / 10} сек
                  </span>
                )}
              </div>

              {(jobMessage || jobStatus === 'running') && (
                <div className="result-message">
                  {jobMessage || 'Ожидание ответа от Revit...'}
                </div>
              )}

              <div className="result-tabs">
                <button
                  className={`result-tab ${resultTab === 'result' ? 'active' : ''}`}
                  onClick={() => setResultTab('result')}
                >
                  Результат
                </button>
                <button
                  className={`result-tab ${resultTab === 'logs' ? 'active' : ''}`}
                  onClick={() => setResultTab('logs')}
                >
                  Логи
                </button>
              </div>

              <div className="result-body">
                {resultTab === 'result' ? (
                  <>
                    {resolvedStats ? (
                      <div className="result-stats">
                        <div className="result-stat">
                          <span className="stat-label">Всего</span>
                          <span className="stat-value">{resolvedStats.total}</span>
                        </div>
                        <div className="result-stat success">
                          <span className="stat-label">Успешно</span>
                          <span className="stat-value">{resolvedStats.processed}</span>
                        </div>
                        <div className="result-stat warning">
                          <span className="stat-label">Пропущено</span>
                          <span className="stat-value">{resolvedStats.skipped}</span>
                        </div>
                        <div className="result-stat error">
                          <span className="stat-label">Ошибки</span>
                          <span className="stat-value">{resolvedStats.errors}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="result-empty">Данных по результату пока нет.</div>
                    )}

                    {jobResult?.summary && (
                      <pre className="result-summary">
                        {JSON.stringify(jobResult.summary, null, 2)}
                      </pre>
                    )}

                    {jobStatus === 'error' && jobResult?.error && (
                      <div className="result-error">{jobResult.error}</div>
                    )}
                  </>
                ) : (
                  <>
                    {hasLogs ? (
                      <div className="log-list">
                        {jobResult?.details?.map((detail, index) => (
                          <div key={detail.id || index} className={`log-item ${detail.status}`}>
                            <span className="log-status">{detail.status}</span>
                            <span className="log-message">{detail.message}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="result-empty">Логи пока пусты.</div>
                    )}
                  </>
                )}
              </div>
            </>
          )}
	      </section>
	    )}
	  </main>
      <ExecutionOverlay
        visible={overlayVisible}
        status={jobStatus}
        toolId={lastTool?.id}
        toolName={lastTool?.name}
        jobId={lastJobId}
        jobDisplayName={friendlyJobName}
        message={jobMessage}
        queueLabel={queueLabel}
        stats={jobResult?.stats || resolvedStats || null}
        summary={jobResult?.summary || null}
        canCancel={jobStatus === 'pending' || jobStatus === 'running'}
        onCancel={handleCancel}
      />

      <ConfirmDialog
        open={Boolean(confirmDialog)}
        title={confirmDialog?.title || ''}
        message={confirmDialog?.message || ''}
        confirmLabel={confirmDialog?.confirmLabel}
        cancelLabel={confirmDialog?.cancelLabel}
        variant={confirmDialog?.variant}
        defaultAction={confirmDialog?.defaultAction}
        onConfirm={() => closeConfirm(true)}
        onCancel={() => closeConfirm(false)}
      />
    </div>
  )
}

function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  variant,
  defaultAction,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: ConfirmVariant
  defaultAction?: 'confirm' | 'cancel'
  onConfirm: () => void
  onCancel: () => void
}) {
  const confirmRef = useRef<HTMLButtonElement | null>(null)
  const cancelRef = useRef<HTMLButtonElement | null>(null)
  const baseId = useId()
  const titleId = `${baseId}-title`
  const messageId = `${baseId}-message`

  useEffect(() => {
    if (!open) return
    const shouldConfirm = (defaultAction || 'cancel') === 'confirm'
    const target = shouldConfirm ? confirmRef.current : cancelRef.current
    target?.focus()
  }, [open, defaultAction])

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onCancel()
        return
      }
      if (event.key !== 'Enter') return

      const target = event.target as HTMLElement | null
      if (target && (target.tagName === 'TEXTAREA' || target.isContentEditable)) return

      event.preventDefault()
      const preferConfirm = (defaultAction || 'cancel') === 'confirm'
      if (preferConfirm) onConfirm()
      else onCancel()
    }

    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [defaultAction, onCancel, onConfirm, open])

  if (!open) return null

  const confirmText = confirmLabel || 'OK'
  const cancelText = cancelLabel || 'Cancel'
  const confirmClass = variant === 'danger' ? 'btn btn-danger' : 'btn btn-secondary'
  const isDanger = variant === 'danger'

  return (
    <div className="apply-progress-overlay confirm-overlay" onClick={onCancel}>
      <div
        className="apply-progress-dialog confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
        onClick={(e) => e.stopPropagation()}
      >
        <div id={titleId} className="confirm-title">
          {isDanger ? <span className="confirm-icon" aria-hidden="true">⚠</span> : null}
          <span>{title}</span>
        </div>
        <div id={messageId} className="confirm-message">{message}</div>
        <div className="confirm-actions">
          <button ref={cancelRef} type="button" className="btn btn-secondary" onClick={onCancel}>
            {cancelText}
          </button>
          <button ref={confirmRef} type="button" className={confirmClass} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
