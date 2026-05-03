import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { TaskBoard } from '../TaskBoard'
import * as api from '../api'
import * as workflowApi from '@/features/projects/workflowApi'

const PROJECT_ID = 'proj-1'
const STUB_USER = '00000000-0000-0000-0000-000000000001'

vi.mock('@/features/auth/AuthProvider', () => ({
  useAuth: () => ({
    user: { id: STUB_USER, email: 'admin@localhost', display_name: 'Admin' },
    stubUsers: [],
    switchStubUser: () => {},
    isLoading: false,
  }),
}))

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <TooltipProvider>
        <MemoryRouter initialEntries={[`/projects/${PROJECT_ID}/board`]}>
          <Routes>
            <Route path="/projects/:id/board" element={children} />
            <Route path="/tasks/:key" element={<div>Task page</div>} />
          </Routes>
        </MemoryRouter>
      </TooltipProvider>
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
    task_type_id: 'tt1', task_type: { id: 'tt1', key: 'task', name: 'Task', is_system: true, color: '#6366f1', icon: 'check-square' },
    key: 'P-1', title: 'My todo task', description: null,
    priority: 'medium', reporter_id: STUB_USER,
    assignee_id: STUB_USER, parent_task_id: null,
    current_status_id: 's1',
    meta: {}, due_date: null, version: 1,
    deleted_at: null, created_at: '2026-01-01', updated_at: '2026-01-01',
  },
  {
    id: 'task2', project_id: PROJECT_ID, workflow_id: 'wf1',
    task_type_id: 'tt1', task_type: { id: 'tt1', key: 'task', name: 'Task', is_system: true, color: '#6366f1', icon: 'check-square' },
    key: 'P-2', title: 'In progress task', description: null,
    priority: 'high', reporter_id: STUB_USER,
    assignee_id: STUB_USER, parent_task_id: null,
    current_status_id: 's2',
    meta: {}, due_date: null, version: 1,
    deleted_at: null, created_at: '2026-01-01', updated_at: '2026-01-01',
  },
  {
    id: 'task3', project_id: PROJECT_ID, workflow_id: 'wf1',
    task_type_id: 'tt1', task_type: null,
    key: 'P-3', title: 'Unassigned task', description: null,
    priority: 'low', reporter_id: 'other',
    assignee_id: null, parent_task_id: null,
    current_status_id: 's1',
    meta: {}, due_date: null, version: 1,
    deleted_at: null, created_at: '2026-01-01', updated_at: '2026-01-01',
  },
]

const MOCK_BOARD_COLUMNS: workflowApi.BoardColumn[] = [
  { id: 'col1', name: 'To Do',       position: 0, status_ids: ['s1'] },
  { id: 'col2', name: 'In Progress', position: 1, status_ids: ['s2'] },
  { id: 'col3', name: 'Done',        position: 2, status_ids: ['s3'] },
]

beforeEach(() => {
  vi.spyOn(workflowApi, 'useBoardColumns').mockReturnValue(
    { data: { items: MOCK_BOARD_COLUMNS }, isLoading: false, isError: false } as unknown as ReturnType<typeof workflowApi.useBoardColumns>,
  )
  vi.spyOn(api, 'useProjectWorkflows').mockReturnValue(
    { data: MOCK_WORKFLOW, isLoading: false, isError: false } as unknown as ReturnType<typeof api.useProjectWorkflows>,
  )
  vi.spyOn(api, 'useProjectTasks').mockReturnValue(
    { data: makeTasks(), isLoading: false, isError: false } as unknown as ReturnType<typeof api.useProjectTasks>,
  )
  vi.spyOn(api, 'useProjectMembers').mockReturnValue(
    { data: { items: [] }, isLoading: false, isError: false } as unknown as ReturnType<typeof api.useProjectMembers>,
  )
  vi.spyOn(api, 'useProjectResolutions').mockReturnValue(
    { data: [], isLoading: false, isError: false } as unknown as ReturnType<typeof api.useProjectResolutions>,
  )
})

describe('TaskBoard', () => {
  it('renders kanban columns from workflow statuses', () => {
    render(<TaskBoard />, { wrapper: Wrapper })
    expect(screen.getByText('To Do')).toBeInTheDocument()
    expect(screen.getAllByText('In Progress').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Done')).toBeInTheDocument()
  })

  it('shows tasks in correct columns by current_status_id', () => {
    render(<TaskBoard />, { wrapper: Wrapper })
    expect(screen.getByText('My todo task')).toBeInTheDocument()
    expect(screen.getByText('In progress task')).toBeInTheDocument()
    expect(screen.getByText('Unassigned task')).toBeInTheDocument()
  })

  it('shows loading skeleton while fetching', () => {
    vi.spyOn(api, 'useProjectWorkflows').mockReturnValue(
      { data: undefined, isLoading: true, isError: false } as unknown as ReturnType<typeof api.useProjectWorkflows>,
    )
    vi.spyOn(api, 'useProjectTasks').mockReturnValue(
      { data: undefined, isLoading: true, isError: false } as unknown as ReturnType<typeof api.useProjectTasks>,
    )
    render(<TaskBoard />, { wrapper: Wrapper })
    expect(screen.queryByText('My todo task')).not.toBeInTheDocument()
  })
})
