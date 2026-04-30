import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { SolutionEditor } from '../SolutionEditor'
import * as api from '@/features/tasks/api'

const create = vi.fn()
const submit = vi.fn()
const update = vi.fn()
const withdraw = vi.fn()

function mockHooks(solution: api.Solution | null) {
  vi.spyOn(api, 'useAssignmentSolution').mockReturnValue(
    { data: solution, isLoading: false } as unknown as ReturnType<typeof api.useAssignmentSolution>,
  )
  vi.spyOn(api, 'useCreateSolution').mockReturnValue(
    { mutateAsync: create, isPending: false } as unknown as ReturnType<typeof api.useCreateSolution>,
  )
  vi.spyOn(api, 'useUpdateSolution').mockReturnValue(
    { mutateAsync: update, isPending: false } as unknown as ReturnType<typeof api.useUpdateSolution>,
  )
  vi.spyOn(api, 'useSubmitSolution').mockReturnValue(
    { mutateAsync: submit, isPending: false } as unknown as ReturnType<typeof api.useSubmitSolution>,
  )
  vi.spyOn(api, 'useWithdrawSolution').mockReturnValue(
    { mutateAsync: withdraw, isPending: false } as unknown as ReturnType<typeof api.useWithdrawSolution>,
  )
}

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  create.mockReset(); submit.mockReset(); update.mockReset(); withdraw.mockReset()
})

describe('SolutionEditor', () => {
  it('shows hint when assignment is not in final status and no solution', () => {
    mockHooks(null)
    render(
      <SolutionEditor projectId="p" taskId="t" assignmentId="a" inFinalStatus={false} taskClosed={false} />,
      { wrapper: Wrapper },
    )
    expect(screen.getByText(/Move your assignment to the final status/i)).toBeInTheDocument()
  })

  it('renders Submit button after typing content; click asks for confirmation', () => {
    mockHooks(null)
    render(
      <SolutionEditor projectId="p" taskId="t" assignmentId="a" inFinalStatus={true} taskClosed={false} />,
      { wrapper: Wrapper },
    )
    const ta = screen.getByPlaceholderText(/Describe your approach/i) as HTMLTextAreaElement
    fireEvent.change(ta, { target: { value: 'my approach' } })
    fireEvent.click(screen.getByRole('button', { name: /Submit Solution/i }))
    expect(screen.getByText(/Submit now\? Decision-maker will be notified/i)).toBeInTheDocument()
  })

  it('shows revision feedback and "Resubmit" button when status=revision_requested', () => {
    mockHooks({
      id: 's', assignment_id: 'a', content: 'old draft', status: 'revision_requested',
      submitted_at: null, revision_comment: 'please add details',
      created_at: '', updated_at: '',
    })
    render(
      <SolutionEditor projectId="p" taskId="t" assignmentId="a" inFinalStatus={true} taskClosed={false} />,
      { wrapper: Wrapper },
    )
    expect(screen.getByText(/please add details/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Resubmit/i })).toBeInTheDocument()
  })

  it('shows Withdraw when submitted, no Submit button', () => {
    mockHooks({
      id: 's', assignment_id: 'a', content: 'submitted text', status: 'submitted',
      submitted_at: '2026-01-01', revision_comment: null,
      created_at: '', updated_at: '',
    })
    render(
      <SolutionEditor projectId="p" taskId="t" assignmentId="a" inFinalStatus={true} taskClosed={false} />,
      { wrapper: Wrapper },
    )
    expect(screen.getByRole('button', { name: /Withdraw/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Submit Solution/i })).not.toBeInTheDocument()
  })
})
