import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import * as api from '../api'
import { ControlPage } from '../ControlPage'

vi.mock('@/features/projects/api', () => ({ useProjectByKey: () => ({ data: { id: 'p1', key: 'P' } }) }))
vi.mock('@/features/tasks/api', () => ({
  useProjectMembers: () => ({ data: { items: [{ user: { id: 'u1', display_name: 'Worker', email: 'w@t' }, role: 'member', is_reviewer: false }] } }),
}))
vi.mock('../api', async importOriginal => ({
  ...(await importOriginal<typeof import('../api')>()),
  useProjectControl: vi.fn(),
}))

describe('ControlPage', () => {
  it('shows waiting reasons and filters by reason', () => {
    vi.mocked(api.useProjectControl).mockReturnValue({ isLoading: false, data: {
      summary: { open_tasks: 2, by_reason: { blocked: 1, session_stale: 1 }, by_specialization: { backend: 2 } },
      items: [
        { id: 't1', key: 'P-1', title: 'Blocked one', task_type: 'task', status: 'To Do', assignee_id: 'u1',
          reviewer_id: null, specialization: 'backend', work_package_version: 1, result_state: 'none',
          active_session: null, blocked_by: ['P-9'], waiting: ['blocked'] },
        { id: 't2', key: 'P-2', title: 'Silent one', task_type: 'execution', status: 'In Progress', assignee_id: 'u1',
          reviewer_id: null, specialization: 'backend', work_package_version: 1, result_state: 'none',
          active_session: { id: 's', user_id: 'u1', machine: 'gpu', started_at: '', last_checkpoint_at: null, silent_hours: 30 },
          blocked_by: [], waiting: ['session_stale'] },
      ],
    } } as unknown as ReturnType<typeof api.useProjectControl>)

    render(
      <MemoryRouter initialEntries={['/projects/P/control']}>
        <Routes><Route path="/projects/:projectKey/control" element={<ControlPage />} /></Routes>
      </MemoryRouter>,
    )
    expect(screen.getByText('Blocked: P-9')).toBeInTheDocument()
    expect(screen.getByText('Session silent 30 h')).toBeInTheDocument()
    expect(screen.getAllByText('Worker')).toHaveLength(2)

    fireEvent.click(screen.getByText('Blocked · 1'))
    expect(vi.mocked(api.useProjectControl)).toHaveBeenLastCalledWith('p1', { reason: 'blocked', specialization: undefined })
  })
})
