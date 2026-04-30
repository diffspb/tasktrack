import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { DecisionPanel } from '../DecisionPanel'
import * as api from '@/features/tasks/api'

const TASK: api.Task = {
  id: 'task-1', project_id: 'p1', workflow_id: 'wf1',
  key: 'P-1', title: 'X', description: null,
  task_type: 'task', priority: 'medium',
  global_status: 'awaiting_decision',
  reporter_id: 'u-rep', decision_maker_id: 'u-dm',
  due_date: null, allow_multi_accept: false, version: 1,
  created_at: '2026-01-01', updated_at: '2026-01-01',
  assignments: [
    { id: 'a1', task_id: 'task-1', user_id: 'lead-1', role: 'lead', current_status_id: 's-final', resolution_id: 'r1', created_at: '2026-01-01' },
    { id: 'a2', task_id: 'task-1', user_id: 'lead-2', role: 'lead', current_status_id: 's-final', resolution_id: 'r1', created_at: '2026-01-01' },
  ],
}

const SOLUTIONS: api.Solution[] = [
  { id: 'sol-1', assignment_id: 'a1', content: 'first approach', status: 'submitted', submitted_at: '2026-01-02', revision_comment: null, created_at: '2026-01-01', updated_at: '2026-01-01' },
  { id: 'sol-2', assignment_id: 'a2', content: 'second approach', status: 'submitted', submitted_at: '2026-01-02', revision_comment: null, created_at: '2026-01-01', updated_at: '2026-01-01' },
]

const make = vi.fn()
const review = vi.fn()

beforeEach(() => {
  vi.spyOn(api, 'useTaskSolutions').mockReturnValue(
    { data: SOLUTIONS, isLoading: false } as unknown as ReturnType<typeof api.useTaskSolutions>,
  )
  vi.spyOn(api, 'useMakeDecision').mockReturnValue(
    { mutateAsync: make, isPending: false } as unknown as ReturnType<typeof api.useMakeDecision>,
  )
  vi.spyOn(api, 'useRequestRevision').mockReturnValue(
    { mutateAsync: review, isPending: false } as unknown as ReturnType<typeof api.useRequestRevision>,
  )
  make.mockReset()
  review.mockReset()
})

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('DecisionPanel', () => {
  it('disables Make Decision until at least one solution is checked', () => {
    render(<DecisionPanel projectId="p1" task={TASK} />, { wrapper: Wrapper })
    const decideBtn = screen.getByRole('button', { name: /Make Decision/i })
    expect(decideBtn).toBeDisabled()

    const checks = screen.getAllByRole('checkbox')
    fireEvent.click(checks[0])
    expect(decideBtn).not.toBeDisabled()
  })

  it('forces single selection when allow_multi_accept=false', () => {
    render(<DecisionPanel projectId="p1" task={TASK} />, { wrapper: Wrapper })
    const checks = screen.getAllByRole('checkbox') as HTMLInputElement[]
    fireEvent.click(checks[0])
    fireEvent.click(checks[1])
    // Picking the second one should clear the first.
    expect(checks[0].checked).toBe(false)
    expect(checks[1].checked).toBe(true)
  })

  it('allows multi selection when allow_multi_accept=true', () => {
    render(<DecisionPanel projectId="p1" task={{ ...TASK, allow_multi_accept: true }} />, { wrapper: Wrapper })
    const checks = screen.getAllByRole('checkbox') as HTMLInputElement[]
    fireEvent.click(checks[0])
    fireEvent.click(checks[1])
    expect(checks[0].checked).toBe(true)
    expect(checks[1].checked).toBe(true)
  })

  it('Request Revision needs exactly one selection and non-empty feedback', () => {
    render(<DecisionPanel projectId="p1" task={TASK} />, { wrapper: Wrapper })
    const reviewBtn = screen.getByRole('button', { name: /Request Revision/i })
    expect(reviewBtn).toBeDisabled()
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    fireEvent.click(reviewBtn)
    // Feedback textarea + send button — send blocked while feedback empty
    const sendBtn = screen.getByRole('button', { name: /Send back for revision/i })
    expect(sendBtn).toBeDisabled()
  })

  it('hides itself when task is not in awaiting_decision/in_revision', () => {
    const { container } = render(
      <DecisionPanel projectId="p1" task={{ ...TASK, global_status: 'in_progress' }} />,
      { wrapper: Wrapper },
    )
    expect(container.firstChild).toBeNull()
  })
})
