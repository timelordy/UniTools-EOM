import React, { useState, useEffect } from "react"
import { Page, Tool, JobResult } from "./types"
import { LogViewer } from "./components/LogViewer"
import { ResultStats } from "./components/ResultStats"
import { TimeSavings, TimeSavingsData } from "./components/TimeSavings"
import "./design-system.css"
import "./styles.css"

const LOGO = "/logo.png"

const FALLBACK_TOOLS: Tool[] = [
  {
    id: "ac-sockets",
    name: "Розетки кондиционеров",
    icon: "/icons/ac-sockets.png",
    description: "Автоматическая расстановка розеток для кондиционеров",
    category: "tools",
  },
  {
    id: "kitchen-sockets",
    name: "Розетки кухни",
    icon: "/icons/kitchen-sockets.png",
    description: "Расстановка розеток на кухне по планировке",
    category: "tools",
  },
  {
    id: "cable-trays",
    name: "Кабельные лотки",
    icon: "/icons/cable-trays.png",
    description: "Построение трасс кабельных лотков",
    category: "tools",
  },
]

const App: React.FC = () => {
  const [tools, setTools] = useState<Tool[]>(FALLBACK_TOOLS)
  const [isLoadingTools, setIsLoadingTools] = useState(false)
  const [page, setPage] = useState<Page>("hub")
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null)
  const [activeTab, setActiveTab] = useState<"hub" | "logs" | "settings">("hub")
  const [activeJob, setActiveJob] = useState<JobResult | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [savingsData, setSavingsData] = useState<TimeSavingsData>({ totalSeconds: 0, executed: {}, history: [] })

  const loadSavings = async () => {
    try {
      // @ts-ignore
      if (window.eel) {
        // @ts-ignore
        const data = await window.eel.get_time_savings()()
        if (data) setSavingsData(data)
      }
    } catch (e) { console.error(e) }
  }

  // Fetch tools and savings on mount
  useEffect(() => {
    loadSavings()
    const loadTools = async () => {
      setIsLoadingTools(true)
      try {
        // @ts-ignore
        if (window.eel) {
          // @ts-ignore
          const response = await window.eel.get_tools_list()()
          if (response && response.success) {
            setTools(response.tools)
          } else {
            console.error("Failed to load tools:", response?.error)
          }
        } else {
          // Fallback for browser dev mode (no python backend)
          console.warn("Eel not found, using fallback tools")
          setTools(FALLBACK_TOOLS)
        }
      } catch (error) {
        console.error("Error loading tools:", error)
      } finally {
        setIsLoadingTools(false)
      }
    }
    loadTools()
  }, [])

  // Polling effect
  useEffect(() => {
    let interval: number | undefined

    if (isPolling && activeJob?.job_id) {
      interval = window.setInterval(async () => {
        // @ts-ignore
        if (window.eel) {
          try {
            // @ts-ignore
            const result = await window.eel.check_job_status(activeJob.job_id)()
            console.log("Job status:", result)

            if (result && result.job_id === activeJob.job_id) {
              setActiveJob(prev => ({ ...prev, ...result }))

              if (result.status === 'completed' || result.status === 'error' || result.status === 'cancelled') {
                setIsPolling(false)

                if (result.status === 'completed' && result.time_saved_minutes) {
                  // Add time saving
                  try {
                    // @ts-ignore
                    await window.eel.add_time_saving(activeJob.tool_id, result.time_saved_minutes)()
                    loadSavings()
                  } catch (e) { console.error("Failed to save time", e) }
                }
              }
            }
          } catch (error) {
            console.error("Polling error:", error)
          }
        } else {
          // Dev mode simulation
          console.log("Polling simulation...")
        }
      }, 1000)
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isPolling, activeJob?.job_id])

  const handleToolClick = (tool: Tool) => {
    setSelectedTool(tool)
    setPage("tools") // In a real app, this would route to a tool-specific form
  }

  const handleBackToMenu = () => {
    setPage("hub")
    setSelectedTool(null)
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <div className="app-brand">
            <div className="app-brand-button">
              {/* <img src={LOGO} alt="EOM Hub" className="app-logo" /> */}
              <span className="app-title">EOM Hub</span>
              <span className="app-version-chip">v1.0.0</span>
            </div>
          </div>
          <div className="header-actions">
            <button
              className={`topbar-tab ${activeTab === 'hub' ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('hub')
                setPage('hub')
                setSelectedTool(null)
              }}
            >
              Инструменты
            </button>
            <button
              className={`topbar-tab ${activeTab === 'logs' ? 'active' : ''}`}
              onClick={() => setActiveTab('logs')}
            >
              Логи {isPolling && "⏳"}
            </button>
            <button
              className={`topbar-tab ${activeTab === 'settings' ? 'active' : ''}`}
              onClick={() => setActiveTab('settings')}
            >
              Настройки
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        {page === "hub" && (
          <div className="tools-page">
            <TimeSavings data={savingsData} />
            <h2 className="page-title">Выберите инструмент</h2>
            <div className="tools-container">
              {Object.entries(
                tools.reduce((acc, tool) => {
                  const group = tool.group || "Other";
                  if (!acc[group]) acc[group] = [];
                  acc[group].push(tool);
                  return acc;
                }, {} as Record<string, Tool[]>)
              ).sort(([a], [b]) => a.localeCompare(b)).map(([group, groupTools]) => (
                <div key={group} className="tool-group">
                  <div className="group-header" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', marginTop: '24px' }}>
                    <span style={{ fontSize: '20px' }}>📁</span>
                    <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>{group}</h3>
                    <span className="badge" style={{ background: 'var(--bg-secondary)', padding: '2px 8px', borderRadius: '12px', fontSize: '12px' }}>
                      {groupTools.length}
                    </span>
                  </div>
                  <div className="tools-grid">
                    {groupTools.map((tool) => (
                      <button
                        key={tool.id}
                        onClick={() => handleToolClick(tool)}
                        className="tool-card"
                      >
                        <div className="tool-icon">
                          {/* Placeholder for icon if image load fails */}
                          <div style={{ fontSize: '32px' }}>🛠️</div>
                        </div>
                        <h3 className="tool-name">{tool.name}</h3>
                        <p className="tool-desc">{tool.description}</p>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {page === "tools" && selectedTool && (
          <div className="tool-panel">
            <div className="tool-panel-header">
              <button className="back-btn" onClick={handleBackToMenu}>
                ← Назад
              </button>
              <h2>{selectedTool.name}</h2>
            </div>

            <div className="tool-description">
              <p>{selectedTool.description}</p>
            </div>

            <div className="step">
              <div className="step-title">
                <div className="step-number">1</div>
                Запуск
              </div>
              <div className="form-group">
                <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
                  Нажмите кнопку ниже, чтобы запустить скрипт инструмента.
                </p>
                <button
                  className="btn btn-primary btn-large"
                  onClick={async () => {
                    if (isStarting) return
                    setIsStarting(true)
                    try {
                      // @ts-ignore
                      if (window.eel) {
                        // @ts-ignore
                        const res = await window.eel.run_tool(selectedTool.id)()
                        if (res.success) {
                          setActiveJob({
                            job_id: res.job_id,
                            tool_id: selectedTool.id,
                            status: 'running',
                            details: []
                          })
                          setIsPolling(true)
                          setActiveTab('logs')
                          setPage('hub')
                          setSelectedTool(null)
                        } else {
                          alert("Error: " + res.error)
                        }
                      } else {
                        alert("Backend not connected (dev mode)")
                      }
                    } catch (e) {
                      console.error(e)
                      alert("Error starting tool")
                    } finally {
                      setIsStarting(false)
                    }
                  }}
                  disabled={isStarting}
                >
                  {isStarting ? "Запуск..." : "Запустить"}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === "logs" && (
          <div className="tools-page">
            <h2 className="page-title">
              Логи выполнения
              {activeJob?.status === 'running' && <span style={{ fontSize: '14px', marginLeft: '10px', color: 'var(--accent)' }}>⏳ Выполняется...</span>}
            </h2>

            {activeJob ? (
              <div className="job-details">
                <div className="job-header" style={{ marginBottom: '16px' }}>
                  <strong>Инструмент:</strong> {activeJob.tool_id} <br />
                  <strong>Статус:</strong> {activeJob.status} <br />
                  {activeJob.error && <div style={{ color: 'red' }}>Ошибка: {activeJob.error}</div>}
                </div>

                {activeJob.stats && <ResultStats stats={activeJob.stats} />}

                <LogViewer logs={activeJob.details || []} />
              </div>
            ) : (
              <div className="empty-state">Нет активных задач</div>
            )}
          </div>
        )}

        {activeTab === "settings" && (
          <div className="tools-page">
            <h2 className="page-title">Настройки</h2>
            <div className="step">
              <div className="form-group">
                <label>Путь к Revit</label>
                <input type="text" placeholder="Автоопределение..." disabled />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
