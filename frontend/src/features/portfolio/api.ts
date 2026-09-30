/**
 * Contract v1.0 with the office and the requirements system (ADR-024): task bases,
 * readiness, impact assessments. Facts are imported via the API; the UI shows and decides.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export interface ExternalObject {
  id: string
  provider: string
  namespace: string
  type: string
  ext_id: string
  locator: string | null
  current_revision: string | null
  revision_state: 'unknown' | 'unconfirmed' | 'current' | 'pending_reconciliation'
  state_as_of: string | null
  status: 'active' | 'revoked'
  is_training: boolean
}

export interface ExternalRevision {
  id: string
  revision: string
  sha256: string | null
  claims: Record<string, unknown>
  observed_at: string
  verified: boolean
}

export type BasisRole = 'cause' | 'input' | 'normative' | 'reference' | 'grant'

export interface Basis {
  id: string
  task_id: string
  object: ExternalObject
  revision: string
  role: BasisRole
  meaning: string | null
  freshness: 'pinned' | 'confirm_current'
  verified: boolean
  created_at: string
  evidence: ExternalRevision[]
}

export interface ReadinessReason {
  code: string
  message: string
  basis_id: string | null
  revision: string | null
  as_of: string | null
}

export interface ReadinessCondition {
  key: 'package' | 'inputs' | 'normative' | 'grant' | 'blockers'
  ok: boolean
  reasons: ReadinessReason[]
  facts: Record<string, unknown>[]
}

export interface Readiness {
  mode: 'standalone' | 'portfolio'
  ready: boolean
  checked_at: string
  conditions: ReadinessCondition[]
}

export interface ImpactAssessment {
  id: string
  task_id: string
  basis_id: string
  old_revision: string
  new_revision: string
  status: 'pending' | 'decided'
  decision: 'continue' | 'reissue' | 'recheck' | 'stop' | null
  rationale: string | null
  authority: string | null
  decided_at: string | null
  created_at: string
}

export function useReadiness(taskId: string) {
  return useQuery<Readiness>({
    queryKey: ['readiness', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/readiness`).then(r => r.data),
  })
}

export function useBases(taskId: string, enabled = true) {
  return useQuery<Basis[]>({
    queryKey: ['bases', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/bases`).then(r => r.data),
    enabled,
  })
}

export function useImpactAssessments(taskId: string, enabled = true) {
  return useQuery<ImpactAssessment[]>({
    queryKey: ['impact-assessments', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/impact-assessments`).then(r => r.data),
    enabled,
  })
}

export interface ImpactDecisionBody {
  decision: 'continue' | 'reissue' | 'recheck' | 'stop'
  rationale: string
  authority?: string
}

export function useDecideImpact(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ImpactDecisionBody }) =>
      api.post(`/impact-assessments/${id}/decide`, body).then(r => r.data),
    onSuccess: () => {
      for (const key of ['impact-assessments', 'readiness', 'bases', 'work-package']) {
        qc.invalidateQueries({ queryKey: [key, taskId] })
      }
    },
  })
}
