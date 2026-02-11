import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ToolCard from './ToolCard'

const baseTool = {
  id: 'lights_center',
  name: 'Свет центр',
  icon: '💡',
  description: 'Размещает светильники',
  category: 'lighting',
  time_saved: 15,
  script_path: 'path/to/script.py',
}

describe('ToolCard', () => {
  it('renders disabled hint in title when card is disabled', () => {
    render(
      <ToolCard
        tool={baseTool}
        isRunning={false}
        executionCount={0}
        onRun={() => {}}
        disabled
      />,
    )

    const button = screen.getByRole('button', { name: /Свет центр/i })
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute('title', expect.stringContaining('Нет подключения к Revit'))
  })

  it('calls onRun when enabled card is clicked', async () => {
    const user = userEvent.setup()
    const onRun = vi.fn()

    render(
      <ToolCard
        tool={baseTool}
        isRunning={false}
        executionCount={1}
        onRun={onRun}
        disabled={false}
      />,
    )

    await user.click(screen.getByRole('button', { name: /Свет центр/i }))
    expect(onRun).toHaveBeenCalledTimes(1)
  })
})
