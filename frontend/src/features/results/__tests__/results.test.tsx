import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ProjectMember, Task } from '@/features/tasks/api'
import * as api from '../api'
import { ResultSection } from '../ResultSection'
import { WorkPackagePanel } from '../WorkPackagePanel'
import { TaskHistory } from '../TaskHistory'
import { SessionPanel } from '../SessionPanel'

vi.mock('../api', async importOriginal => {
  const real = await importOriginal<typeof import('../api')>()
  const mutation = () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false })
  return {
    ...real,
    useProposals: vi.fn(), useWorkPackage: vi.fn(), useTaskHistory: vi.fn(), useSessions: vi.fn(),
    useSubmitProposal: mutation, useWithdrawProposal: mutation, useReviewProposal: mutation,
    useProposeDelivery: mutation, useRecordRecipientAcceptance: mutation,
    useSaveWorkPackageDraft: mutation, useIssueWorkPackage: mutation,
    useClaimTask: mutation, useSessionAction: mutation,
  }
})

const WORKER = 'u-worker', REVIEWER = 'u-reviewer', OTHER = 'u-other'

const members: ProjectMember[] = [
  { user: { id: WORKER, display_name: 'Worker', email: 'w@t' }, role: 'member', is_reviewer: false },
  { user: { id: REVIEWER, display_name: 'Reviewer', email: 'r@t' }, role: 'member', is_reviewer: true },
  { user: { id: OTHER, display_name: 'Other', email: 'o@t' }, role: 'member', is_reviewer: false },
]

const task = (over: Partial<Task> = {}): Task => ({
  id: 't1', key: 'P-1', project_id: 'p1', workflow_id: 'wf', task_type_id: 'tt', task_type: null,
  reporter_id: OTHER, assignee_id: WORKER, parent_task_id: null, current_status_id: 's1',
  title: 'Report', description: null, priority: 'medium', meta: {}, start_date: null, due_date: null,
  duration_days: null, version: 3, work_package_version: 1, reviewer_id: null, result_state: 'proposed',
  delivery: null, recipient_acceptance: null, deleted_at: null, created_at: '2026-09-30', updated_at: '2026-09-30',
  ...over,
})

const PACKAGE: api.WorkPackageStateResponse = {
  state: 'issued', draft: null,
  current: {
    id: 'wp1', task_id: 't1', version: 1, digest: 'abcdef0123456789', issued_by: OTHER, created_at: '2026-09-30',
    content: {
      goal: 'Make a report', expected_result: 'PDF', specialization: 'analytics',
      criteria: [{ key: 'c1', text: 'All sections filled', required: true }], inputs: [], constraints: [],
    },
  },
}

const proposal = (over: Partial<api.Proposal> = {}): api.Proposal => ({
  id: 'p1', task_id: 't1', version: 1, author_id: WORKER, work_package_id: 'wp1', supersedes_id: null,
  session_id: null, status: 'submitted', summary: 'Report is ready', links: [{ kind: 'pr', url: 'https://x/pr/1' }],
  criteria: [{ key: 'c1', status: 'met' }], checks: [], limitations: null, provenance: {},
  created_at: '2026-09-30T10:00:00Z', reviews: [], ...over,
})

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.mocked(api.useWorkPackage).mockReturnValue({ data: PACKAGE } as ReturnType<typeof api.useWorkPackage>)
  vi.mocked(api.useProposals).mockReturnValue({ data: [proposal()] } as ReturnType<typeof api.useProposals>)
})

describe('ResultSection', () => {
  it('shows the review form to a reviewer who is neither author nor assignee', () => {
    wrap(<ResultSection task={task()} currentUserId={REVIEWER} members={members} />)
    expect(screen.getByText('Report is ready')).toBeInTheDocument()
    expect(screen.getByTestId('review-form')).toBeInTheDocument()
    expect(screen.getByLabelText('Verdict c1')).toBeInTheDocument()
  })

  it('hides the review form from the author and lets them submit a new version', () => {
    wrap(<ResultSection task={task()} currentUserId={WORKER} members={members} />)
    expect(screen.queryByTestId('review-form')).not.toBeInTheDocument()
    expect(screen.getByText('New version')).toBeInTheDocument()
    expect(screen.getByText('Withdraw')).toBeInTheDocument()
  })

  it('hides the review form from a member without the reviewer profile', () => {
    wrap(<ResultSection task={task()} currentUserId={OTHER} members={members} />)
    expect(screen.queryByTestId('review-form')).not.toBeInTheDocument()
  })

  it('respects the designated reviewer', () => {
    wrap(<ResultSection task={task({ reviewer_id: OTHER })} currentUserId={REVIEWER} members={members} />)
    expect(screen.queryByTestId('review-form')).not.toBeInTheDocument()
  })

  it('shows reviews with their rationale', () => {
    vi.mocked(api.useProposals).mockReturnValue({ data: [proposal({
      status: 'changes_requested',
      reviews: [{ id: 'r1', proposal_id: 'p1', reviewer_id: REVIEWER, verdict: 'changes_requested',
        criteria: [], rationale: 'Section 3 missing', created_at: '2026-09-30T11:00:00Z' }],
    })] } as ReturnType<typeof api.useProposals>)
    wrap(<ResultSection task={task({ result_state: 'changes_requested' })} currentUserId={OTHER} members={members} />)
    expect(screen.getByText('Section 3 missing')).toBeInTheDocument()
    expect(screen.getAllByText('Changes requested').length).toBeGreaterThan(0)
  })

  it('offers delivery only after acceptance', () => {
    vi.mocked(api.useProposals).mockReturnValue({ data: [proposal({ status: 'accepted' })] } as ReturnType<typeof api.useProposals>)
    wrap(<ResultSection task={task({ result_state: 'accepted' })} currentUserId={WORKER} members={members} />)
    expect(screen.getByLabelText('Delivery target')).toBeInTheDocument()
  })
})

describe('WorkPackagePanel', () => {
  it('shows the issued version with its criteria', () => {
    wrap(<WorkPackagePanel task={task()} canEdit={false} />)
    expect(screen.getByText('Make a report')).toBeInTheDocument()
    expect(screen.getByText('All sections filled')).toBeInTheDocument()
    expect(screen.getByText(/v1 · abcdef01/)).toBeInTheDocument()
    expect(screen.queryByText('Edit')).not.toBeInTheDocument()
  })

  it('says the task is not ready without an assignment', () => {
    vi.mocked(api.useWorkPackage).mockReturnValue(
      { data: { state: 'none', draft: null, current: null } } as ReturnType<typeof api.useWorkPackage>,
    )
    wrap(<WorkPackagePanel task={task()} canEdit />)
    expect(screen.getByText(/not ready for execution/)).toBeInTheDocument()
    expect(screen.getByText('Write')).toBeInTheDocument()
  })
})

describe('TaskHistory', () => {
  it('renders audit events with reason and changed fields', () => {
    vi.mocked(api.useTaskHistory).mockReturnValue({ isLoading: false, data: { next_cursor: null, items: [{
      id: 1, cursor: '1.1', occurred_at: '2026-09-30T10:00:00Z', actor_id: OTHER, project_id: 'p1', task_id: 't1',
      session_id: 's1', entity_type: 'task', entity_id: 't1', action: 'updated', reason: 'clarified',
      before: { title: 'Old', version: 1 }, after: { title: 'New', version: 2 },
    }] } } as ReturnType<typeof api.useTaskHistory>)
    wrap(<TaskHistory taskId="t1" nameOf={id => (id === OTHER ? 'Other' : id)} />)
    expect(screen.getByText('Other')).toBeInTheDocument()
    expect(screen.getByText(/clarified/)).toBeInTheDocument()
    expect(screen.getByText('New')).toBeInTheDocument()
    expect(screen.getByText('session')).toBeInTheDocument()
  })
})

describe('SessionPanel', () => {
  it('offers the assignee to start a session', () => {
    vi.mocked(api.useSessions).mockReturnValue({ data: [] } as unknown as ReturnType<typeof api.useSessions>)
    wrap(<SessionPanel task={task()} currentUserId={WORKER} isManager={false} nameOf={id => id} />)
    expect(screen.getByText('Start work session')).toBeInTheDocument()
  })

  it('shows the active session of another user and lets a manager release it', () => {
    vi.mocked(api.useSessions).mockReturnValue({ data: [{
      id: 's1', task_id: 't1', user_id: WORKER, work_package_id: 'wp1', role: 'executor', state: 'active',
      machine: 'gpu-1', workdir: null, client: null, created_at: '2026-09-30T10:00:00Z', last_checkpoint_at: null,
      ended_at: null, ended_by: null, end_reason: null, result: null, checkpoints: [],
    }] } as unknown as ReturnType<typeof api.useSessions>)
    wrap(<SessionPanel task={task()} currentUserId={OTHER} isManager nameOf={() => 'Worker'} />)
    expect(screen.getByText(/on gpu-1/)).toBeInTheDocument()
    expect(screen.getByText('Release session…')).toBeInTheDocument()
    expect(screen.queryByText('Checkpoint')).not.toBeInTheDocument()
  })
})
