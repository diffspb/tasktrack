import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as api from '../api'
import { TaskView } from '../TaskView'

const { ME, BOSS } = vi.hoisted(() => ({ ME: 'u-me', BOSS: 'u-boss' }))

vi.mock('../api', async importOriginal => {
  const real = await importOriginal<typeof import('../api')>()
  const q = (data: unknown) => () => ({ data })
  return {
    ...real,
    useDisplayWorkflows: q([{
      id: 'wf', name: 'Basic', is_default: true, created_at: '2026-01-01',
      statuses: [
        { id: 's1', name: 'To Do', category: 'initial', is_default: true, position: 0, color: null },
        { id: 's2', name: 'In Progress', category: 'intermediate', is_default: false, position: 1, color: null },
        { id: 's3', name: 'Done', category: 'final', is_default: false, position: 2, color: null },
      ],
      transitions: [
        { id: 't1', from_status_id: 's1', to_status_id: 's2' },
        { id: 't2', from_status_id: 's1', to_status_id: 's3' },
      ],
    }, {
      // system process workflow (ADR-023), returned with include_used_system
      id: 'sys-research', name: 'Исследование', is_default: false, created_at: '2026-01-01',
      statuses: [
        { id: 'r1', name: 'Open', category: 'initial', is_default: true, position: 0, color: null },
        { id: 'r2', name: 'Investigating', category: 'intermediate', is_default: false, position: 1, color: null },
      ],
      transitions: [{ id: 'rt1', from_status_id: 'r1', to_status_id: 'r2' }],
    }]),
    useProjectMembers: q({ items: [
      { user: { id: ME, display_name: 'Me', email: 'me@t' }, role: 'member', is_reviewer: false },
      { user: { id: BOSS, display_name: 'Boss', email: 'b@t' }, role: 'manager', is_reviewer: true },
    ] }),
    useTask: q(undefined),
    useChildTasks: q([]),
    useTaskComments: q([]),
    useTaskLinks: q([]),
    useLinkTypes: q([]),
    useDeleteTaskLink: () => ({ mutate: vi.fn() }),
    useUpdateTask: () => ({ mutateAsync: vi.fn() }),
    useTransitionStatus: vi.fn(),
  }
})

vi.mock('@/features/results/api', async importOriginal => {
  const real = await importOriginal<typeof import('@/features/results/api')>()
  const mutation = () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false })
  return {
    ...real,
    useWorkPackage: () => ({ data: { state: 'none', draft: null, current: null } }),
    useProposals: () => ({ data: [] }),
    useSessions: () => ({ data: [] }),
    useTaskHistory: () => ({ data: { items: [], next_cursor: null }, isLoading: false }),
    useSubmitProposal: mutation, useWithdrawProposal: mutation, useReviewProposal: mutation,
    useProposeDelivery: mutation, useRecordRecipientAcceptance: mutation,
    useSaveWorkPackageDraft: mutation, useIssueWorkPackage: mutation,
    useClaimTask: mutation, useSessionAction: mutation,
  }
})

vi.mock('../CommentSection', () => ({ CommentSection: () => <div>comments</div> }))
vi.mock('../LinkTaskDialog', () => ({ LinkTaskDialog: () => null }))
vi.mock('../CreateTaskModal', () => ({ CreateTaskModal: () => null }))

const task: api.Task = {
  id: 't1', key: 'P-7', project_id: 'p1', workflow_id: 'wf', task_type_id: 'tt',
  task_type: { id: 'tt', key: 'execution', name: 'Исполнение', is_system: true, color: null, icon: null },
  reporter_id: BOSS, assignee_id: ME, parent_task_id: null, current_status_id: 's1',
  title: 'Migrate metrics', description: 'Move the module', priority: 'high', meta: {},
  start_date: null, due_date: null, duration_days: null, version: 2, work_package_version: null,
  reviewer_id: null, result_state: 'none', delivery: null, recipient_acceptance: null,
  deleted_at: null, created_at: '2026-09-30', updated_at: '2026-09-30',
}

function wrap(t: api.Task = task) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter><TaskView task={t} mode="page" currentUserId={ME} /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('TaskView', () => {
  beforeEach(() => {
    vi.mocked(api.useTransitionStatus).mockReturnValue(
      { mutateAsync: vi.fn(), isPending: false } as unknown as ReturnType<typeof api.useTransitionStatus>,
    )
  })

  it('renders the task with assignment, result and session blocks', () => {
    wrap()
    expect(screen.getByText('Migrate metrics')).toBeInTheDocument()
    expect(screen.getByTestId('work-package')).toBeInTheDocument()
    expect(screen.getByTestId('result-section')).toBeInTheDocument()
    expect(screen.getByText('Submit result')).toBeInTheDocument()   // I am the assignee
    expect(screen.getByText('Start work session')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()     // next status button
  })

  it('explains why a process task cannot be closed without review', async () => {
    vi.mocked(api.useTransitionStatus).mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockRejectedValue({ response: { data: { detail: { code: 'RESULT_NOT_REVIEWED' } } } }),
    } as unknown as ReturnType<typeof api.useTransitionStatus>)
    wrap()
    fireEvent.click(screen.getByRole('button', { name: 'Done' }))
    await waitFor(() => expect(screen.getByText(/closes only after its result is reviewed/)).toBeInTheDocument())
  })

  it('lists missing fields required by a transition', async () => {
    vi.mocked(api.useTransitionStatus).mockReturnValue({
      isPending: false,
      mutateAsync: vi.fn().mockRejectedValue({
        response: { data: { detail: { code: 'TRANSITION_FIELDS_REQUIRED', missing: ['estimate'] } } },
      }),
    } as unknown as ReturnType<typeof api.useTransitionStatus>)
    wrap()
    fireEvent.click(screen.getByRole('button', { name: 'In Progress' }))
    await waitFor(() => expect(screen.getByText('Fill in first: estimate.')).toBeInTheDocument())
  })

  it('shows the durable history tab', () => {
    wrap()
    fireEvent.click(screen.getByText('History'))
    expect(screen.getByText('No history.')).toBeInTheDocument()
  })

  it("uses the task's own process workflow, not the project default", () => {
    wrap({ ...task, workflow_id: 'sys-research', current_status_id: 'r1' })
    expect(screen.getByRole('button', { name: 'Investigating' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'In Progress' })).not.toBeInTheDocument()
  })
})
