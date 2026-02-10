import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './design-system.css'
import './styles.css'

function ensureEelBridge(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve()
  if ((window as typeof window & { eel?: unknown }).eel) return Promise.resolve()

  return new Promise((resolve) => {
    let settled = false
    const done = () => {
      if (settled) return
      settled = true
      resolve()
    }

    const existing = document.getElementById('eel-bridge-script') as HTMLScriptElement | null
    if (existing) {
      if ((window as typeof window & { eel?: unknown }).eel) {
        done()
        return
      }
      existing.addEventListener('load', done, { once: true })
      existing.addEventListener('error', done, { once: true })
      window.setTimeout(done, 1500)
      return
    }

    const script = document.createElement('script')
    script.src = '/eel.js'
    script.id = 'eel-bridge-script'
    script.async = false
    script.defer = false
    script.addEventListener('load', done, { once: true })
    script.addEventListener('error', done, { once: true })
    document.head.appendChild(script)
    window.setTimeout(done, 1500)
  })
}

ensureEelBridge().finally(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  )
})
