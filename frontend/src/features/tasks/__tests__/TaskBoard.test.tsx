import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/features/auth/AuthProvider'
import { TaskBoard } from '../TaskBoard'
import * as api from '../api'

const PROJECT_ID = 'proj-1'
const STUB_USER = '00000000-0000-0000-0000-000000000001'

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <TooltipProvider>
          <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/board`]}>
            <Routes>
              <Route path="/projects/:id/board" element={children} />
            </Routes>
          </MemoryRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

const MOCK_WORKFLOW: api.Workflow[] = [{
  id: 'wf1', name: 'Basic', is_default: true, created_at: '2026-01-01',
  statuses: [
    { id: 's1', name: 'To Do',       category: 'initial',       is_default: true,  position: 0, color: null },
    { id: 's2', name: 'In Progress', category: 'intermediate',  is_default: false, position: 1, color: null },
    { id: 's3', name: 'Done',        category: 'final',         is_default: false, position: 2, color: null },
  ],
  transitions: [
    { id: 't1', from_status_id: 's1', to_status_id: 's2' },
    { id: 't2', from_status_id: 's2', to_status_id: 's3' },
  ],
}]

const makeTasks = (): api.Task[] => [
  {
    id: 'task1', project_id: PROJECT_ID, workflow_id: 'wf1',
    key: 'P-1', title: 'My todo task', description: null,
    task_type: 'task', priority: 'medium', global_status: 'open',
    reporter_id: STUB_USER, decision_maker_id: null,
    due_date: null, version: 1, created_at: '2026-01-01', updated_at: '2026-01-01',
    assignments: [{ id: 'a1', task_id: 'task1', user_id: STUB_USER, role: 'lead', current_status_id: 's1', resolution_id: null, created_at: '2026-01-01' }],
  },
  {
    id: 'task2', project_id: PROJECT_ID, workflow_id: 'wf1',
    key: 'P-2', title: 'In progress task', description: null,
    task_type: 'task', priority: 'high', global_status: 'in_progress',
    reporter_id: STUB_USER, decision_maker_id: null,
    due_date: null, version: 1, created_at: '2026-01-01', updated_at: '2026-01-01',
    assignments: [{ id: 'a2', task_id: 'task2', user_id: STUB_USER, role: 'lead', current_status_id: 's2', resolution_id: null, created_at: '2026-01-01' }],
  },
  {
    id: 'task3', project_id: PROJECT_ID, workflow_id: 'wf1',
    key: 'P-3', title: 'Not assigned to me', description: null,
    task_type: 'task', priority: 'low', global_status: 'open',
    reporter_id: 'other', decision_maker_id: null,
    due_date: null, version: 1, created_at: '2026-01-01', updated_at: '2026-01-01',
    assignments: [{ id: 'a3', task_id: 'task3', user_id: 'other-user', role: 'lead', current_status_id: 's1', resolution_id: null, created_at: '2026-01-01' }],
  },
]

beforeEach(() => {
  vi.spyOn(api, 'useProjectWorkflows').mockReturnValue(
    { data: MOCK_WORKFLOW, isLoading: false, isError: false } as unknown as ReturnType<typeof api.useProjectWorkflows>,
  )
  vi.spyOn(api, 'useProjectTasks').mockReturnValue(
    { data: makeTasks(), isLoading: false, isError: false } as unknown as ReturnType<typeof api.useProjectTasks>,
  )
  vi.spyOn(api, 'useProjectResolutions').mockReturnValue(
    { data: [], isLoading: false, isError: false } as unknown as ReturnType<typeof api.useProjectResolutions>,
  )
})

describe('TaskBoard', () => {
  it('renders kanban columns from workflow statuses', () => {
    render(<TaskBoard />, { wrapper: Wrapper })
    // Column headers are rendered as uppercase spans — use getAllByText since
    // "In Progress" also appears on task card status badges
    expect(screen.getByText('To Do')).toBeInTheDocument()
    expect(screen.getAllByText('In Progress').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Done')).toBeInTheDocument()
  })

  it('shows tasks assigned to current user in correct columns', () => {
    render(<TaskBoard />, { wrapper: Wrapper })
    expect(screen.getByText('My todo task')).toBeInTheDocument()
    expect(screen.getByText('In progress task')).toBeInTheDocument()
  })

  it('does not show tasks not assigned to current user', () => {
    render(<TaskBoard />, { wrapper: Wrapper })
    expect(screen.queryByText('Not assigned to me')).not.toBeInTheDocument()
  })

  it('shows loading skeleton while fetching', () => {
    vi.spyOn(api, 'useProjectWorkflows').mockReturnValue(
      { data: undefined, isLoading: true, isError: false } as unknown as ReturnType<typeof api.useProjectWorkflows>,
    )
    vi.spyOn(api, 'useProjectTasks').mockReturnValue(
      { data: undefined, isLoading: true, isError: false } as unknown as ReturnType<typeof api.useProjectTasks>,
    )
    render(<TaskBoard />, { wrapper: Wrapper })
    // Skeletons rendered — no task titles visible
    expect(screen.queryByText('My todo task')).not.toBeInTheDocument()
  })
})
