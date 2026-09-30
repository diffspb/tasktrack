import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import * as api from '../api'
import { ReadinessPanel } from '../ReadinessPanel'

const decide = vi.fn()

vi.mock('../api', async importOriginal => {
  const real = await importOriginal<typeof import('../api')>()
  return {
    ...real,
    useReadiness: vi.fn(), useBases: vi.fn(), useImpactAssessments: vi.fn(),
    useDecideImpact: () => ({ mutate: decide, isPending: false }),
  }
})

const OBJ: api.ExternalObject = {
  id: 'o1', provider: 'req', namespace: 'proj-pack', type: 'requirement', ext_id: 'REQ-12', locator: null,
  current_revision: 'v2', revision_state: 'current', state_as_of: '2026-09-30T10:00:00Z', status: 'active',
  is_training: false,
}

const WAITING: api.Readiness = {
  mode: 'portfolio', ready: false, checked_at: '2026-09-30T10:00:00Z',
  conditions: [
    { key: 'package', ok: true, reasons: [], facts: [] },
    { key: 'inputs', ok: false, facts: [], reasons: [
      { code: 'INPUT_NOT_ACCEPTED', message: 'вход verification_plan/VP-3@1 не принят для использования',
        basis_id: 'b2', revision: '1', as_of: null }] },
    { key: 'normative', ok: true, reasons: [], facts: [] },
    { key: 'grant', ok: false, facts: [], reasons: [
      { code: 'NO_GRANT', message: 'нет выделения ресурса или разрешения', basis_id: null, revision: null, as_of: null }] },
    { key: 'blockers', ok: false, facts: [], reasons: [
      { code: 'IMPACT_PENDING', message: 'новая редакция requirement/REQ-12: v1 → v2', basis_id: null,
        revision: 'v2', as_of: null }] },
  ],
}

const PENDING: api.ImpactAssessment = {
  id: 'ia1', task_id: 't1', basis_id: 'b1', old_revision: 'v1', new_revision: 'v2', status: 'pending',
  decision: null, rationale: null, authority: null, decided_at: null, created_at: '2026-09-30T10:00:00Z',
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

function mockData(readiness: api.Readiness, bases: api.Basis[] = [], assessments: api.ImpactAssessment[] = []) {
  vi.mocked(api.useReadiness).mockReturnValue({ data: readiness } as ReturnType<typeof api.useReadiness>)
  vi.mocked(api.useBases).mockReturnValue({ data: bases } as ReturnType<typeof api.useBases>)
  vi.mocked(api.useImpactAssessments).mockReturnValue({ data: assessments } as ReturnType<typeof api.useImpactAssessments>)
}

beforeEach(() => decide.mockClear())

describe('ReadinessPanel', () => {
  it('shows nothing for a standalone project', () => {
    mockData({ mode: 'standalone', ready: true, checked_at: '2026-09-30T10:00:00Z', conditions: [] })
    const { container } = wrap(<ReadinessPanel taskId="t1" isManager />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows waiting reasons and bases with pinned and current revisions', () => {
    mockData(WAITING, [{
      id: 'b1', task_id: 't1', object: OBJ, revision: 'v1', role: 'normative', meaning: null, freshness: 'pinned',
      verified: true, created_at: '2026-09-30', evidence: [{ id: 'e1', revision: '1', sha256: 'x', verified: true,
        observed_at: '2026-09-30', claims: { kind: 'compliance_conclusion', outcome: 'complies' } }],
    }])
    wrap(<ReadinessPanel taskId="t1" isManager={false} />)
    expect(screen.getByText('Waiting')).toBeInTheDocument()
    expect(screen.getByText(/не принят для использования/)).toBeInTheDocument()
    expect(screen.getByText(/нет выделения ресурса/)).toBeInTheDocument()
    expect(screen.getByText('requirement/REQ-12@v1')).toBeInTheDocument()
    expect(screen.getByText('current v2')).toBeInTheDocument()
    expect(screen.getByText('compliance_conclusion: complies')).toBeInTheDocument()
  })

  it('lets a manager continue on the old revision only with rationale and authority', () => {
    mockData(WAITING, [], [PENDING])
    wrap(<ReadinessPanel taskId="t1" isManager />)
    const cont = screen.getByRole('button', { name: 'Continue on old' })
    fireEvent.change(screen.getByLabelText('Rationale'), { target: { value: 'не касается пилота' } })
    expect(cont).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Authority'), { target: { value: 'OD-9' } })
    fireEvent.click(cont)
    expect(decide).toHaveBeenCalledWith({ id: 'ia1', body: {
      decision: 'continue', rationale: 'не касается пилота', authority: 'OD-9' } })
  })

  it('does not offer the decision to a non-manager', () => {
    mockData(WAITING, [], [PENDING])
    wrap(<ReadinessPanel taskId="t1" isManager={false} />)
    expect(screen.getByTestId('impact-assessment')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Reissue' })).toBeNull()
  })
})
