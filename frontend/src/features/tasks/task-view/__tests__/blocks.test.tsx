import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import * as api from '../../api'
import { TitleEditor } from '../TitleEditor'
import { DatesBlock } from '../DatesBlock'
import { ChildTasks } from '../ChildTasks'

const { mutateAsync } = vi.hoisted(() => ({ mutateAsync: vi.fn() }))

vi.mock('../../api', async importOriginal => ({
  ...(await importOriginal<typeof import('../../api')>()),
  useUpdateTask: () => ({ mutateAsync }),
  useChildTasks: vi.fn(),
}))
vi.mock('../../CreateTaskModal', () => ({ CreateTaskModal: () => null }))

const task = {
  id: 't1', key: 'P-1', project_id: 'p1', workflow_id: 'wf', task_type_id: 'tt', task_type: null,
  reporter_id: 'u', assignee_id: null, parent_task_id: null, current_status_id: 's1', title: 'Old title',
  description: null, priority: 'medium', meta: {}, start_date: '2026-10-01', due_date: null, duration_days: null,
  version: 4, work_package_version: null, reviewer_id: null, result_state: 'none', delivery: null,
  recipient_acceptance: null, deleted_at: null, created_at: '2026-09-30', updated_at: '2026-09-30',
} as api.Task

beforeEach(() => mutateAsync.mockClear())

describe('task view blocks', () => {
  it('saves an edited title with the task version', async () => {
    render(<TitleEditor task={task} mode="page" />)
    fireEvent.click(screen.getByText('Old title'))
    const input = screen.getByDisplayValue('Old title')
    fireEvent.change(input, { target: { value: 'New title' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ title: 'New title', version: 4 }))
  })

  it('does not save an unchanged title', async () => {
    render(<TitleEditor task={task} mode="panel" />)
    fireEvent.click(screen.getByText('Old title'))
    fireEvent.keyDown(screen.getByDisplayValue('Old title'), { key: 'Enter' })
    expect(mutateAsync).not.toHaveBeenCalled()
  })

  it('clears a date', () => {
    render(<DatesBlock task={task} />)
    expect(screen.getByText('Not set')).toBeInTheDocument()   // due date
    fireEvent.click(screen.getAllByRole('button').find(b => b.querySelector('svg'))!)
    expect(mutateAsync).toHaveBeenCalledWith({ start_date: null, version: 4 })
  })

  it('shows a subtask status from its own (process) workflow', () => {
    vi.mocked(api.useChildTasks).mockReturnValue({ data: [
      { ...task, id: 'c1', key: 'P-2', title: 'Research child', current_status_id: 'r2', parent_task_id: 't1' },
    ] } as ReturnType<typeof api.useChildTasks>)
    render(
      <MemoryRouter>
        <ChildTasks task={task} statuses={[
          { id: 's1', name: 'To Do', category: 'initial', is_default: true, position: 0, color: null },
          { id: 'r2', name: 'Investigating', category: 'intermediate', is_default: false, position: 1, color: null },
        ]} />
      </MemoryRouter>,
    )
    expect(screen.getByText('Research child')).toBeInTheDocument()
    expect(screen.getByText('Investigating')).toBeInTheDocument()
  })
})
