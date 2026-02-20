import { useReducer, useEffect, useCallback, useMemo, useRef, useId } from 'react'
import ToolCard from './components/ToolCard'
import TimeSavingsCounter from './components/TimeSavingsCounter'
import ExecutionOverlay from './components/ExecutionOverlay'
import StatusBar from './components/StatusBar'

// Eel interface
declare global {
  interface Window {
    eel: {
      get_tools_config(): () => Promise<ToolsConfig>
      get_revit_status(): () => Promise<RevitStatus>
      run_tool(toolId: string, jobId?: string): () => Promise<RunResult>
      get_job_result(jobId: string): () => Promise<JobResult | null>
      get_time_savings(): () => Promise<TimeSavings>
      add_time_saving(toolId: string, minutes: number | { min: number; max: number }): () => Promise<TimeSavings>
      reset_time_savings(): () => Promise<TimeSavings>
    }
  }
}

interface Tool {
  id: string
  name: string
  icon: string
  description: string
  category: string
  time_saved: number // fallback: minutes per run
  script_path: string
}

interface Category {
  id: string
  name: string
  icon: string
  order: number
}

interface ToolsConfig {
  tools: Record<string, Tool>
  categories: Record<string, Category>
  dangerous_tools?: string[]
  warning_messages?: Record<string, string>
}

interface RevitStatus {
  connected: boolean
  document?: string
  documentPath?: string
  revitVersion?: string
  sessionId?: string
}

interface RunResult {
  success: boolean
  job_id?: string
  tool_id?: string
  message?: string
  error?: string
}

type JobStatus = 'idle' | 'pending' | 'running' | 'completed' | 'error' | 'cancelled'

interface JobStats {
  total: number
  processed: number
  skipped: number
  errors: number
}

interface JobDetail {
  id: string
  status: string
  message: string
  number?: string
  level?: string
}

interface JobResult {
  job_id: string
  tool_id: string
  status?: string
  message?: string
  error?: string
  executionTime?: number
  stats?: JobStats
  details?: JobDetail[]
  summary?: Record<string, unknown>
}

interface TimeSavings {
  totalSeconds: number
  totalSecondsMin?: number
  totalSecondsMax?: number
  executed: Record<string, number>
  history: Array<{
    tool_id: string
    minutes: number
    minutes_min?: number
    minutes_max?: number
    timestamp: number
    time: string
  }>
}

type ConfirmVariant = 'default' | 'danger'

type UxErrorContext = 'revit_not_ready' | 'run_dispatch' | 'job_poll' | 'cancel' | 'startup'

interface UxErrorInfo {
  code: string
  title: string
  message: string
  nextAction?: string
  technicalMessage?: string
  canRetry: boolean
}

type ResultTab = 'result' | 'logs'

interface ConfirmDialogState {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: ConfirmVariant
  defaultAction?: 'confirm' | 'cancel'
}

const normalizeErrorMessage = (error: unknown): string => {
  if (!error) return ''
  if (error instanceof Error) return error.message || ''
  if (typeof error === 'string') return error
  if (typeof error === 'object') {
    const value = error as { message?: unknown; error?: unknown }
    if (typeof value.message === 'string' && value.message.trim()) return value.message
    if (typeof value.error === 'string' && value.error.trim()) return value.error
  }
  return ''
}

const includesAny = (text: string, patterns: string[]): boolean => {
  return patterns.some((pattern) => text.includes(pattern))
}

export const mapUxError = (error: unknown, context: UxErrorContext): UxErrorInfo => {
  const technicalMessage = normalizeErrorMessage(error).trim()
  const source = technicalMessage.toLowerCase()

  if (context === 'revit_not_ready') {
    return {
      code: 'REVIT_NOT_READY',
      title: 'Revit пока не готов',
      message: 'Инструмент нельзя запустить без активного подключения к Revit.',
      nextAction: 'Откройте проект в Revit, нажмите кнопку Hub и дождитесь статуса «Подключено».',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  if (includesAny(source, ['cancelled', 'canceled', 'отмен'])) {
    return {
      code: 'JOB_CANCELLED',
      title: 'Выполнение остановлено',
      message: 'Запуск был отменён до завершения.',
      nextAction: 'Проверьте состояние модели и запустите инструмент повторно при необходимости.',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  if (includesAny(source, ['timeout', 'timed out', 'eel bridge timeout', 'время ожидания'])) {
    return {
      code: 'HUB_TIMEOUT',
      title: 'Слишком долгий ответ от Hub',
      message: 'Hub или Revit отвечают слишком долго, запуск не завершился вовремя.',
      nextAction: 'Проверьте нагрузку в Revit и повторите запуск через несколько секунд.',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  if (includesAny(source, ['failed to fetch', 'networkerror', 'err_connection', 'connection refused', 'http 500', 'http 502', 'http 503'])) {
    return {
      code: 'HUB_UNREACHABLE',
      title: 'Нет связи с Hub',
      message: 'Не удалось связаться с локальным сервером Hub.',
      nextAction: 'Проверьте, что Hub запущен в Revit, и попробуйте снова.',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  if (includesAny(source, ['http 401', 'http 403', 'unauthorized', 'forbidden', 'access denied'])) {
    return {
      code: 'ACCESS_DENIED',
      title: 'Недостаточно прав для запуска',
      message: 'Hub отклонил запрос из-за ограничений доступа.',
      nextAction: 'Перезапустите Revit/Hub под нужной учётной записью или проверьте права.',
      technicalMessage: technicalMessage || undefined,
      canRetry: false,
    }
  }

  if (includesAny(source, ['http 404', 'not found'])) {
    return {
      code: 'TOOL_NOT_FOUND',
      title: 'Инструмент недоступен',
      message: 'Запрошенный инструмент не найден или временно недоступен.',
      nextAction: 'Обновите Hub и проверьте конфигурацию инструментов.',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  if (context === 'cancel') {
    return {
      code: 'CANCEL_FAILED',
      title: 'Не удалось отменить запуск',
      message: 'Команда отмены не была доставлена в Revit.',
      nextAction: 'Подождите завершения задачи или повторите отмену.',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  if (context === 'startup') {
    return {
      code: 'STARTUP_FAILED',
      title: 'Не удалось загрузить Hub',
      message: 'Не получилось получить стартовые данные от сервера.',
      nextAction: 'Проверьте подключение к Revit и обновите окно Hub.',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  if (context === 'job_poll') {
    return {
      code: 'JOB_FAILED',
      title: 'Инструмент завершился с ошибкой',
      message: 'Во время выполнения возникла ошибка обработки.',
      nextAction: 'Проверьте логи результата, исправьте данные модели и повторите запуск.',
      technicalMessage: technicalMessage || undefined,
      canRetry: true,
    }
  }

  return {
    code: 'RUN_FAILED',
    title: 'Не удалось выполнить инструмент',
    message: 'Команда не выполнилась из-за непредвиденной ошибки.',
    nextAction: 'Повторите запуск. Если ошибка повторяется, проверьте подключение Hub и данные проекта.',
    technicalMessage: technicalMessage || undefined,
    canRetry: true,
  }
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

interface JobMeta {
  toolId: string
  minutes: number
}

interface AppState {
  config: ToolsConfig | null
  status: RevitStatus
  savings: TimeSavings
  pendingJobIds: string[]
  jobMetaById: Record<string, JobMeta>
  countedJobIds: Record<string, true>
  jobDisplayNameById: Record<string, string>
  activeCategory: string | null
  showConnectionHelp: boolean
  lastTool: Tool | null
  lastJobId: string | null
  jobStatus: JobStatus
  jobResult: JobResult | null
  jobMessage: string
  uxError: UxErrorInfo | null
  resultTab: ResultTab
  overlayJobId: string | null
  confirmDialog: ConfirmDialogState | null
}

type AppStateAction =
  | { type: 'merge'; payload: Partial<AppState> }
  | { type: 'update'; updater: (state: AppState) => AppState }

const initialAppState: AppState = {
  config: null,
  status: { connected: false },
  savings: { totalSeconds: 0, executed: {}, history: [] },
  pendingJobIds: [],
  jobMetaById: {},
  countedJobIds: {},
  jobDisplayNameById: {},
  activeCategory: null,
  showConnectionHelp: false,
  lastTool: null,
  lastJobId: null,
  jobStatus: 'idle',
  jobResult: null,
  jobMessage: '',
  uxError: null,
  resultTab: 'result',
  overlayJobId: null,
  confirmDialog: null,
}

const appStateReducer = (state: AppState, action: AppStateAction): AppState => {
  if (action.type === 'merge') {
    return { ...state, ...action.payload }
  }
  return action.updater(state)
}

function useAppController() {
  const [state, dispatch] = useReducer(appStateReducer, initialAppState)
  const configLoadedRef = useRef(false)
  const jobRunCountersRef = useRef<Record<string, number>>({})
  const overlayHideTimerRef = useRef<number | null>(null)
  const confirmResolveRef = useRef<((value: boolean) => void) | null>(null)

  const mergeState = useCallback((payload: Partial<AppState>) => {
    dispatch({ type: 'merge', payload })
  }, [])

  const updateState = useCallback((updater: (current: AppState) => AppState) => {
    dispatch({ type: 'update', updater })
  }, [])

  const requestConfirm = useCallback((next: ConfirmDialogState) => {
    return new Promise<boolean>((resolve) => {
      confirmResolveRef.current = resolve
      mergeState({ confirmDialog: next })
    })
  }, [mergeState])

  const closeConfirm = useCallback((value: boolean) => {
    const resolve = confirmResolveRef.current
    confirmResolveRef.current = null
    mergeState({ confirmDialog: null })
    resolve?.(value)
  }, [mergeState])

  const setUxErrorFrom = useCallback((error: unknown, context: UxErrorContext): UxErrorInfo => {
    const mapped = mapUxError(error, context)
    mergeState({ uxError: mapped, jobMessage: mapped.message })
    return mapped
  }, [mergeState])

  const {
    config,
    status,
    savings,
    pendingJobIds,
    jobMetaById,
    countedJobIds,
    jobDisplayNameById,
    activeCategory,
    showConnectionHelp,
    lastTool,
    lastJobId,
    jobStatus,
    jobResult,
    jobMessage,
    uxError,
    resultTab,
    overlayJobId,
    confirmDialog,
  } = state

  useEffect(() => {
    return () => {
      const resolve = confirmResolveRef.current
      confirmResolveRef.current = null
      resolve?.(false)
    }
  }, [])

  useEffect(() => {
    return () => {
      if (overlayHideTimerRef.current != null) {
        window.clearTimeout(overlayHideTimerRef.current)
        overlayHideTimerRef.current = null
      }
    }
  }, [])

  // Load config and status.
  useEffect(() => {
    const loadData = async () => {
      try {
        const [cfg, st, sv] = await Promise.all([getToolsConfig(), getRevitStatus(), getTimeSavings()])
        configLoadedRef.current = true
        mergeState({ config: cfg, status: st, savings: sv })
      } catch (e) {
        console.error('Failed to load data:', e)
        mergeState({ jobStatus: 'error' })
        setUxErrorFrom(e, 'startup')
      }
    }

    void loadData()

    const interval = window.setInterval(async () => {
      try {
        if (!configLoadedRef.current) {
          const [cfg, sv] = await Promise.all([getToolsConfig(), getTimeSavings()])
          configLoadedRef.current = true
          mergeState({ config: cfg, savings: sv })
        }

        const st = await getRevitStatus()
        mergeState({ status: st })
      } catch {
        // ignore
      }
    }, 5000)

    return () => window.clearInterval(interval)
  }, [mergeState, setUxErrorFrom])

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
            } catch (error) {
              return {
                jobId,
                res: {
                  job_id: jobId,
                  tool_id: '',
                  status: 'error',
                  error: (error as Error).message,
                } as JobResult,
              }
            }
          }),
        )

        for (const { jobId, res } of results) {
          if (!res) continue

          const nextStatus = (res.status as JobStatus) || 'completed'
          const isTerminal = nextStatus === 'completed' || nextStatus === 'error' || nextStatus === 'cancelled'

          if (jobId === lastJobId) {
            updateState((current) => {
              if (current.lastJobId !== jobId) return current

              const next: AppState = {
                ...current,
                jobResult: res,
                jobStatus: nextStatus,
              }

              if (nextStatus === 'error') {
                const mapped = mapUxError(res.error || res.message || `Задача ${jobId} завершилась с ошибкой`, 'job_poll')
                next.uxError = mapped
                next.jobMessage = mapped.message
              } else if (nextStatus === 'cancelled') {
                const mapped = mapUxError(res.error || res.message || 'cancelled', 'job_poll')
                next.uxError = mapped
                next.jobMessage = mapped.message
              } else {
                next.uxError = null
                if (res.message) next.jobMessage = res.message
                else if (res.error) next.jobMessage = res.error
              }

              return next
            })
          }

          if (nextStatus === 'completed' && !countedJobIds[jobId]) {
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

            const toolIdForSaving = meta?.toolId || res.tool_id || null

            // Fallback: treat tool.time_saved as per-run minutes.
            if ((minutesMin == null || minutesMax == null) && meta) {
              minutesMin = meta.minutes
              minutesMax = meta.minutes
            }

            if (minutesMin != null && minutesMax != null && minutesMax > 0 && toolIdForSaving) {
              try {
                const newSavings = await addTimeSaving(toolIdForSaving, { min: minutesMin, max: minutesMax })
                mergeState({ savings: newSavings })
              } catch {
                // ignore
              }
            }

            updateState((current) => {
              if (current.countedJobIds[jobId]) return current
              return {
                ...current,
                countedJobIds: { ...current.countedJobIds, [jobId]: true },
              }
            })
          }

          if (isTerminal) {
            updateState((current) => {
              const nextPending = current.pendingJobIds.filter((id) => id !== jobId)
              if (!current.jobMetaById[jobId] && nextPending.length === current.pendingJobIds.length) {
                return current
              }

              const nextJobMeta = { ...current.jobMetaById }
              delete nextJobMeta[jobId]

              return {
                ...current,
                pendingJobIds: nextPending,
                jobMetaById: nextJobMeta,
              }
            })
          } else {
            updateState((current) => {
              if (current.pendingJobIds.includes(jobId)) return current
              return {
                ...current,
                pendingJobIds: [...current.pendingJobIds, jobId],
              }
            })
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
  }, [pendingJobIds, lastJobId, countedJobIds, jobMetaById, mergeState, updateState])

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

    let nextOverlayId: string | null = null
    if (jobStatus === 'error' && uxError) {
      nextOverlayId = '__ux_error__'
    } else if (lastTool && lastJobId && (jobStatus === 'pending' || jobStatus === 'running' || jobStatus === 'completed')) {
      nextOverlayId = lastJobId
    }

    mergeState({ overlayJobId: nextOverlayId })

    if (jobStatus === 'completed' && lastTool && lastJobId) {
      overlayHideTimerRef.current = window.setTimeout(() => {
        updateState((current) => {
          if (current.overlayJobId !== lastJobId) return current
          return { ...current, overlayJobId: null }
        })
        overlayHideTimerRef.current = null
      }, 1300)
    }
  }, [jobStatus, lastJobId, lastTool, uxError, mergeState, updateState])

  useEffect(() => {
    if (status.connected && showConnectionHelp) {
      mergeState({ showConnectionHelp: false })
    }
  }, [status.connected, showConnectionHelp, mergeState])

  const handleRunTool = useCallback(async (tool: Tool) => {
    if (!status.connected) {
      mergeState({
        lastTool: tool,
        lastJobId: null,
        jobResult: null,
        jobStatus: 'error',
        showConnectionHelp: true,
        resultTab: 'result',
      })
      setUxErrorFrom(null, 'revit_not_ready')
      return
    }

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

    mergeState({
      lastTool: tool,
      lastJobId: null,
      jobResult: null,
      jobMessage: '',
      uxError: null,
      jobStatus: 'pending',
      resultTab: 'result',
    })

    try {
      const result = await runTool(tool.id)

      if (result.success) {
        mergeState({
          uxError: null,
          lastJobId: result.job_id || null,
          jobMessage: result.message || 'Команда отправлена в Revit',
        })

        const jobId = result.job_id
        if (jobId) {
          const baseName = tool.name?.trim() || 'Задача'
          const prevCount = jobRunCountersRef.current[tool.id] || 0
          const nextCount = prevCount + 1
          jobRunCountersRef.current = { ...jobRunCountersRef.current, [tool.id]: nextCount }
          const computedFriendlyName = `${baseName}_${nextCount}`

          updateState((current) => ({
            ...current,
            pendingJobIds: current.pendingJobIds.includes(jobId) ? current.pendingJobIds : [...current.pendingJobIds, jobId],
            jobMetaById: {
              ...current.jobMetaById,
              [jobId]: { toolId: tool.id, minutes: tool.time_saved },
            },
            jobDisplayNameById: {
              ...current.jobDisplayNameById,
              [jobId]: computedFriendlyName,
            },
          }))
        }
      } else {
        mergeState({ lastJobId: null, jobStatus: 'error' })
        setUxErrorFrom(result.error || result.message || 'Не удалось отправить команду в Revit', 'run_dispatch')
      }
    } catch (error) {
      console.error('Failed to run tool:', error)
      mergeState({ lastJobId: null, jobStatus: 'error' })
      setUxErrorFrom(error, 'run_dispatch')
    }
  }, [config, mergeState, requestConfirm, setUxErrorFrom, status.connected, updateState])

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
      mergeState({ savings: newSavings })
    } catch (error) {
      console.error('Failed to reset savings:', error)
      mergeState({ jobStatus: 'error' })
      setUxErrorFrom(error, 'startup')
    }
  }, [mergeState, requestConfirm, setUxErrorFrom])

  const handleCancel = useCallback(async () => {
    if (!jobStatus || jobStatus === 'completed' || jobStatus === 'error' || jobStatus === 'cancelled') return

    try {
      if (lastJobId) {
        await runTool('cancel', lastJobId)
      } else {
        await runTool('cancel')
      }
      mergeState({ uxError: null, jobMessage: 'Запрос на отмену отправлен...' })
    } catch (error) {
      console.error('Failed to cancel:', error)
      mergeState({ jobStatus: 'error' })
      setUxErrorFrom(error, 'cancel')
    }
  }, [jobStatus, lastJobId, mergeState, setUxErrorFrom])

  const toolsByCategory = useMemo(() => {
    if (!config) return {} as Record<string, Tool[]>

    return Object.values(config.tools).reduce((acc, tool) => {
      if (!acc[tool.category]) acc[tool.category] = []
      acc[tool.category].push(tool)
      return acc
    }, {} as Record<string, Tool[]>)
  }, [config])

  const sortedCategories = useMemo(() => {
    if (!config) return [] as Category[]
    return Object.values(config.categories).sort((a, b) => a.order - b.order)
  }, [config])

  const filteredCategories = useMemo(() => {
    return activeCategory
      ? sortedCategories.filter((category) => category.id === activeCategory)
      : sortedCategories
  }, [activeCategory, sortedCategories])

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

    const processed = details.filter((detail) => detail.status === 'success').length
    const skipped = details.filter((detail) => detail.status === 'skipped').length
    const errors = details.filter((detail) => detail.status === 'error').length

    return {
      total: details.length,
      processed,
      skipped,
      errors,
    }
  }, [jobResult])

  const hasLogs = Boolean(jobResult?.details && jobResult.details.length)

  const setActiveCategory = useCallback((categoryId: string | null) => {
    mergeState({ activeCategory: categoryId })
  }, [mergeState])

  const toggleConnectionHelp = useCallback(() => {
    updateState((current) => ({
      ...current,
      showConnectionHelp: !current.showConnectionHelp,
    }))
  }, [updateState])

  const setResultTab = useCallback((tab: ResultTab) => {
    mergeState({ resultTab: tab })
  }, [mergeState])

  const overlayVisible = Boolean(
    (jobStatus === 'error' && uxError) || (lastTool && lastJobId && overlayJobId && overlayJobId === lastJobId),
  )

  return {
    activeCategory,
    closeConfirm,
    confirmDialog,
    filteredCategories,
    friendlyJobName,
    handleCancel,
    handleResetSavings,
    handleRunTool,
    hasLogs,
    jobMessage,
    jobResult,
    jobStatus,
    jobStatusLabel,
    lastJobId,
    lastTool,
    overlayVisible,
    queueLabel,
    resolvedStats,
    resultTab,
    runningToolIds,
    savings,
    setActiveCategory,
    setResultTab,
    showConnectionHelp,
    sortedCategories,
    status,
    toggleConnectionHelp,
    toolsByCategory,
    uxError,
  }
}

function App() {
  const {
    activeCategory,
    closeConfirm,
    confirmDialog,
    filteredCategories,
    friendlyJobName,
    handleCancel,
    handleResetSavings,
    handleRunTool,
    hasLogs,
    jobMessage,
    jobResult,
    jobStatus,
    jobStatusLabel,
    lastJobId,
    lastTool,
    overlayVisible,
    queueLabel,
    resolvedStats,
    resultTab,
    runningToolIds,
    savings,
    setActiveCategory,
    setResultTab,
    showConnectionHelp,
    sortedCategories,
    status,
    toggleConnectionHelp,
    toolsByCategory,
    uxError,
  } = useAppController()

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
          {sortedCategories.map((cat) => (
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
              onClick={toggleConnectionHelp}
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
          {filteredCategories.map((category) => (
            <section key={category.id} className="category-section">
              <h2 className="category-title">
                <span className="category-icon">{category.icon}</span>
                {category.name}
                <span className="category-count">{toolsByCategory[category.id]?.length || 0}</span>
              </h2>
              <div className="tools-grid">
                {toolsByCategory[category.id]?.map((tool) => (
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
                <div className={`result-status status-${jobStatus}`}>{jobStatusLabel}</div>
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

            {!lastJobId && <div className="result-empty">Запустите инструмент, чтобы увидеть результат.</div>}

            {lastJobId && (
              <>
                <div className="result-meta">
                  <span className="result-meta-item" title={lastJobId || undefined}>
                    Задача: {friendlyJobName || lastJobId}
                  </span>
                  {jobResult?.executionTime != null && (
                    <span className="result-meta-item" style={{ fontWeight: 'bold', color: '#4CAF50' }}>
                      ⏱ Время: {Math.round(jobResult.executionTime * 10) / 10} сек
                    </span>
                  )}
                </div>

                {(jobMessage || jobStatus === 'running') && (
                  <div className="result-message">{jobMessage || 'Ожидание ответа от Revit...'}</div>
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

                      {jobResult?.summary && <pre className="result-summary">{JSON.stringify(jobResult.summary, null, 2)}</pre>}

                      {jobStatus === 'error' && (
                        <div className="result-error">{uxError?.message || jobResult?.error || jobMessage}</div>
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
        uxError={uxError}
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
    <div className="apply-progress-overlay confirm-overlay">
      <button
        type="button"
        className="confirm-overlay-backdrop"
        onClick={onCancel}
        aria-label="Закрыть окно подтверждения"
      />
      <div
        className="apply-progress-dialog confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={messageId}
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
