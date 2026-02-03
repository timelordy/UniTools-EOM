import { useState, useEffect, useCallback, useMemo } from 'react'
import ToolCard from './components/ToolCard'
import TimeSavingsCounter from './components/TimeSavingsCounter'
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

function App() {
  const [config, setConfig] = useState<ToolsConfig | null>(null)
  const [status, setStatus] = useState<RevitStatus>({ connected: false })
  const [savings, setSavings] = useState<TimeSavings>({ totalSeconds: 0, executed: {}, history: [] })
  const [, setRunningTool] = useState<string | null>(null)
  const [pendingJobIds, setPendingJobIds] = useState<string[]>([])
  const [jobMetaById, setJobMetaById] = useState<Record<string, { toolId: string; minutes: number }>>({})
  const [countedJobIds, setCountedJobIds] = useState<Record<string, true>>({})
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [lastTool, setLastTool] = useState<Tool | null>(null)
  const [lastJobId, setLastJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<JobStatus>('idle')
  const [jobResult, setJobResult] = useState<JobResult | null>(null)
  const [jobMessage, setJobMessage] = useState<string>('')
  const [resultTab, setResultTab] = useState<'result' | 'logs'>('result')

  // Load config and status
  useEffect(() => {
    const loadData = async () => {
      try {
        if (window.eel) {
          const cfg = await window.eel.get_tools_config()()
          setConfig(cfg)

          const st = await window.eel.get_revit_status()()
          setStatus(st)

          const sv = await window.eel.get_time_savings()()
          setSavings(sv)
        }
      } catch (e) {
        console.error('Failed to load data:', e)
      }
    }

    loadData()

    // Poll status every 5 seconds
    const interval = setInterval(async () => {
      if (window.eel) {
        try {
          const st = await window.eel.get_revit_status()()
          setStatus(st)
        } catch {
          // ignore
        }
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  // Poll all queued jobs so tools are independent.
  useEffect(() => {
    if (!window.eel) return

    let stopped = false

    const poll = async () => {
      if (stopped) return

      const jobIds = Array.from(new Set([...(pendingJobIds || []), ...(lastJobId ? [lastJobId] : [])]))
      if (!jobIds.length) return

      try {
        const results = await Promise.all(
          jobIds.map(async (jobId) => {
            try {
              const res = await window.eel.get_job_result(jobId)()
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
                const newSavings = await window.eel.add_time_saving(toolIdForSaving, { min: minutesMin, max: minutesMax })()
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

  const handleRunTool = useCallback(async (tool: Tool) => {
    if (!window.eel) return

    if (!status.connected) {
      setLastTool(tool)
      setJobStatus('error')
      setJobMessage('Revit не готов. Откройте проект и нажмите кнопку Hub в Revit, затем повторите.')
      setResultTab('result')
      return
    }

    // Check for dangerous tools
    if (config?.dangerous_tools?.includes(tool.id)) {
      const msg = config.warning_messages?.[tool.id] || config.warning_messages?.default || 'Продолжить?'
      if (!confirm(msg)) return
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
      const result = await window.eel.run_tool(tool.id)()

      if (result.success) {
        setLastJobId(result.job_id || null)
        setJobMessage(result.message || 'Команда отправлена в Revit')
        const jobId = result.job_id
        if (jobId) {
          setPendingJobIds((prev) => (prev.includes(jobId) ? prev : [...prev, jobId]))
          setJobMetaById((prev) => ({ ...prev, [jobId]: { toolId: tool.id, minutes: tool.time_saved } }))
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
  }, [config, status.connected])

  const handleResetSavings = useCallback(async () => {
    if (!window.eel) return
    if (!confirm('Сбросить весь прогресс экономии времени?')) return

    try {
      const newSavings = await window.eel.reset_time_savings()()
      setSavings(newSavings)
    } catch (e) {
      console.error('Failed to reset savings:', e)
    }
  }, [])

  const handleCancel = useCallback(async () => {
    if (!window.eel) return
    if (!jobStatus || jobStatus === 'completed' || jobStatus === 'error' || jobStatus === 'cancelled') return

    try {
      // Send cancel command with current job ID if available, or just generic cancel
      // Based on script.py logic, "run:cancel:jobId" is handled.
      // run_tool('cancel', lastJobId) -> "run:cancel:lastJobId"
      await window.eel.run_tool('cancel', lastJobId || undefined)()
      setJobStatus('cancelled')
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
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-text">UniTools</span>
            <span className="logo-icon">EOM</span>
          </div>
          <StatusBar status={status} />
        </div>
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

        <section className="result-panel">
          <div className="result-header">
            <div className="result-title">
              <span>Результат запуска</span>
              {lastTool && <span className="result-tool">{lastTool.name}</span>}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className={`result-status status-${jobStatus}`}>
                {jobStatusLabel}
              </div>
              {(jobStatus === 'running' || jobStatus === 'pending') && (
                <button
                  onClick={handleCancel}
                  title="Отменить выполнение"
                  style={{
                    background: '#fee2e2',
                    border: '1px solid #ef4444',
                    color: '#ef4444',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    padding: '2px 8px',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}
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
                <span className="result-meta-item">Job: {lastJobId}</span>
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
      </main>
    </div>
  )
}

export default App
