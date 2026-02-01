export type Page = 'hub' | 'tools' | 'settings' | 'about'

export interface Tool {
  id: string
  name: string
  icon: string
  description: string
  category: string
  group?: string
  requirements?: string[] | null
  isDangerous?: boolean
  warningMessage?: string
}

export interface LogEntry {
  id: string
  status: "success" | "error" | "info" | "warning"
  message: string
}

export interface JobStats {
  total: number
  processed: number
  skipped: number
  errors: number
}

export interface JobResult {
  job_id: string
  tool_id: string
  status: "running" | "completed" | "error" | "cancelled"
  executionTime?: number
  stats?: JobStats
  error?: string
  details?: LogEntry[]
  time_saved_minutes?: number
}


export interface RevitStatus {
  success: boolean
  connected: boolean
  document?: string | null
  documentPath?: string | null
  revitVersion?: string | null
  message: string
  error?: string
}

export interface ApiResponse {
  success: boolean
  error?: string
  message?: string
  warnings?: string[]
  tools?: Tool[]
  tool?: Tool
}

declare global {
  interface Window {
    eel: any
  }
}
