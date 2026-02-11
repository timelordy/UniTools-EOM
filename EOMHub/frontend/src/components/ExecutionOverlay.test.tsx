import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ExecutionOverlay from './ExecutionOverlay'

describe('ExecutionOverlay', () => {
  it('shows actionable UX error block when status is error', () => {
    render(
      <ExecutionOverlay
        visible
        status="error"
        toolName="Magic Tool"
        message="Техническая ошибка"
        uxError={{
          code: 'HUB_UNREACHABLE',
          title: 'Нет связи с Hub',
          message: 'Не удалось связаться с сервером Hub.',
          nextAction: 'Проверьте, что Hub запущен.',
          canRetry: true,
        }}
        canCancel={false}
      />,
    )

    expect(screen.getByText('Нет связи с Hub')).toBeInTheDocument()
    expect(screen.getByText('Не удалось связаться с сервером Hub.')).toBeInTheDocument()
    expect(screen.getByText('Проверьте, что Hub запущен.')).toBeInTheDocument()
  })

  it('calls cancel handler on cancel button click while running', async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()

    render(
      <ExecutionOverlay
        visible
        status="running"
        toolName="Magic Tool"
        message="Выполнение..."
        canCancel
        onCancel={onCancel}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Отменить (Esc)' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })
})
