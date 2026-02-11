import { describe, expect, it } from 'vitest'
import { mapUxError } from './App'

describe('mapUxError', () => {
  it('maps disconnected Revit state into actionable UX message', () => {
    const mapped = mapUxError(null, 'revit_not_ready')

    expect(mapped.code).toBe('REVIT_NOT_READY')
    expect(mapped.message).toContain('активного подключения к Revit')
    expect(mapped.nextAction).toContain('нажмите кнопку Hub')
    expect(mapped.canRetry).toBe(true)
  })

  it('maps timeout errors to HUB_TIMEOUT', () => {
    const mapped = mapUxError(new Error('Eel bridge timeout after 1200ms'), 'run_dispatch')

    expect(mapped.code).toBe('HUB_TIMEOUT')
    expect(mapped.title).toContain('Слишком долгий ответ')
    expect(mapped.canRetry).toBe(true)
  })

  it('maps network failures to HUB_UNREACHABLE', () => {
    const mapped = mapUxError(new Error('Failed to fetch'), 'run_dispatch')

    expect(mapped.code).toBe('HUB_UNREACHABLE')
    expect(mapped.message).toContain('локальным сервером Hub')
  })

  it('falls back to generic startup error', () => {
    const mapped = mapUxError(new Error('unknown issue'), 'startup')

    expect(mapped.code).toBe('STARTUP_FAILED')
    expect(mapped.nextAction).toContain('обновите окно Hub')
  })
})
