/**
 * Assignment (work package), result proposals, reviews, work sessions, task history,
 * manager's control view — ADR-020…023, FR-003.
 */
import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import type { Task } from '@/features/tasks/api'

// ── Work package ────────────────────────────────────────────────────────────

export interface Criterion { key?: string | null; text: string; required: boolean }
export interface PackageInput { kind: string; ref: string; version?: string | null; note?: string | null }

export interface WorkPackageContent {
  goal: string | null
  expected_result: string | null
  criteria: Criterion[]
  inputs: PackageInput[]
  constraints: string[]
  specialization: string | null
}

export interface WorkPackage {
  id: string
  task_id: string
  version: number
  /** Issued content: every criterion has its stable key (c1, c2…). */
  content: Omit<WorkPackageContent, 'criteria'> & { criteria: { key: string; text: string; required: boolean }[] }
  digest: string
  issued_by: string
  created_at: string
}

export type PackageState = 'none' | 'draft' | 'issued' | 'draft_changed'

export interface WorkPackageStateResponse {
  state: PackageState
  draft: WorkPackageContent | null
  current: WorkPackage | null
}

export function useWorkPackage(taskId: string) {
  return useQuery<WorkPackageStateResponse>({
    queryKey: ['work-package', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/work-package`).then(r => r.data),
  })
}

export function useSaveWorkPackageDraft(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (content: WorkPackageContent) =>
      api.put(`/tasks/${taskId}/work-package/draft`, content).then(r => r.data),
    onSuccess: data => qc.setQueryData(['work-package', taskId], data),
  })
}

export function useIssueWorkPackage(task: Task) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post(`/tasks/${task.id}/work-package/issue`).then(r => r.data as WorkPackage),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['work-package', task.id] })
      invalidateTask(qc, task)
    },
  })
}

// ── Result proposals and reviews ────────────────────────────────────────────

export type ProposalStatus =
  | 'submitted' | 'accepted' | 'changes_requested' | 'rejected' | 'withdrawn' | 'superseded' | 'historical'
export type Verdict = 'accepted' | 'changes_requested' | 'rejected'

export interface ProposalLink { kind: 'pr' | 'commit' | 'release' | 'build' | 'document' | 'other'; url: string; ref?: string | null }
export interface ProposalCriterion { key: string; status: 'met' | 'not_met' | 'not_applicable'; evidence?: string | null }
export interface ProposalCheck { name: string; result: 'passed' | 'failed' | 'skipped'; details?: string | null }

export interface Review {
  id: string
  proposal_id: string
  reviewer_id: string
  verdict: Verdict
  criteria: { key: string; verdict: 'met' | 'not_met'; note?: string | null }[]
  rationale: string
  created_at: string
}

export interface Proposal {
  id: string
  task_id: string
  version: number
  author_id: string
  work_package_id: string | null
  supersedes_id: string | null
  session_id: string | null
  status: ProposalStatus
  summary: string
  links: ProposalLink[]
  criteria: ProposalCriterion[]
  checks: ProposalCheck[]
  limitations: string | null
  provenance: Record<string, unknown>
  created_at: string
  reviews: Review[]
}

export interface ProposalInput {
  summary: string
  links?: ProposalLink[]
  criteria?: ProposalCriterion[]
  checks?: ProposalCheck[]
  limitations?: string | null
  supersedes_id?: string | null
}

export interface ReviewInput {
  verdict: Verdict
  rationale: string
  criteria: { key: string; verdict: 'met' | 'not_met'; note?: string | null }[]
}

export function useProposals(taskId: string) {
  return useQuery<Proposal[]>({
    queryKey: ['proposals', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/proposals`).then(r => r.data),
  })
}

export function useSubmitProposal(task: Task) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProposalInput) => api.post(`/tasks/${task.id}/proposals`, data).then(r => r.data),
    onSuccess: () => afterResultChange(qc, task),
  })
}

export function useWithdrawProposal(task: Task) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (proposalId: string) => api.post(`/proposals/${proposalId}/withdraw`).then(r => r.data),
    onSuccess: () => afterResultChange(qc, task),
  })
}

export function useReviewProposal(task: Task) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ proposalId, ...data }: ReviewInput & { proposalId: string }) =>
      api.post(`/proposals/${proposalId}/reviews`, data).then(r => r.data),
    onSuccess: () => afterResultChange(qc, task),
  })
}

export type ReviewQueueItem = Proposal & { task: { id: string; key: string; title: string; project_id: string } }

export function useReviewQueue(projectId?: string) {
  return useQuery<ReviewQueueItem[]>({
    queryKey: ['review-queue', projectId ?? 'all'],
    queryFn: () => api.get('/review-queue', { params: projectId ? { project_id: projectId } : {} }).then(r => r.data),
  })
}

export function useProposeDelivery(task: Task) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { target: string; ref?: string | null; note?: string | null }) =>
      api.post(`/tasks/${task.id}/delivery`, data).then(r => r.data as Task),
    onSuccess: updated => setTask(qc, updated),
  })
}

export function useRecordRecipientAcceptance(task: Task) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { accepted_by: string; accepted_at: string; source: string; ref?: string | null }) =>
      api.post(`/tasks/${task.id}/recipient-acceptance`, data).then(r => r.data as Task),
    onSuccess: updated => setTask(qc, updated),
  })
}

// ── Work sessions ───────────────────────────────────────────────────────────

export interface WorkSession {
  id: string
  task_id: string
  user_id: string
  work_package_id: string | null
  role: 'executor' | 'reviewer'
  state: 'active' | 'completed' | 'released'
  machine: string | null
  workdir: string | null
  client: string | null
  created_at: string
  last_checkpoint_at: string | null
  ended_at: string | null
  ended_by: string | null
  end_reason: string | null
  result: string | null
  checkpoints: { id: string; note: string; data: Record<string, unknown>; created_at: string }[]
}

export function useSessions(taskId: string) {
  return useQuery<WorkSession[]>({
    queryKey: ['sessions', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/sessions`).then(r => r.data),
  })
}

export function useClaimTask(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { machine?: string; workdir?: string; client?: string }) =>
      api.post(`/tasks/${taskId}/sessions`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions', taskId] }),
  })
}

export function useSessionAction(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sessionId, action, body }: {
      sessionId: string; action: 'complete' | 'release' | 'checkpoints'; body: Record<string, unknown>
    }) => api.post(`/sessions/${sessionId}/${action}`, body).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions', taskId] }),
  })
}

// ── History (audit log) ─────────────────────────────────────────────────────

export interface AuditEvent {
  id: number
  cursor: string
  occurred_at: string
  actor_id: string | null
  project_id: string | null
  task_id: string | null
  session_id: string | null
  entity_type: string
  entity_id: string
  action: string
  reason: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
}

export function useTaskHistory(taskId: string, enabled = true) {
  return useQuery<{ items: AuditEvent[]; next_cursor: string | null }>({
    queryKey: ['task-history', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/history`, { params: { limit: 500 } }).then(r => r.data),
    enabled,
  })
}

// ── Manager's control view ──────────────────────────────────────────────────

export type WaitingReason =
  | 'no_work_package' | 'work_package_changed' | 'no_assignee' | 'blocked' | 'awaiting_review'
  | 'changes_requested' | 'session_stale' | 'awaiting_recipient' | 'unverified_result'

export interface ControlItem {
  id: string
  key: string
  title: string
  task_type: string | null
  status: string
  assignee_id: string | null
  reviewer_id: string | null
  specialization: string | null
  work_package_version: number | null
  result_state: string
  active_session: {
    id: string; user_id: string; machine: string | null; started_at: string
    last_checkpoint_at: string | null; silent_hours: number
  } | null
  blocked_by: string[]
  waiting: WaitingReason[]
}

export interface ControlOverview {
  summary: {
    open_tasks: number
    by_reason: Partial<Record<WaitingReason, number>>
    by_specialization: Record<string, number>
  }
  items: ControlItem[]
}

export function useProjectControl(projectId: string | undefined, filters: { reason?: string; specialization?: string }) {
  return useQuery<ControlOverview>({
    queryKey: ['control', projectId, filters],
    queryFn: () => api.get(`/projects/${projectId}/control`, {
      params: Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    }).then(r => r.data),
    enabled: !!projectId,
  })
}

// ── Members: reviewer profile ───────────────────────────────────────────────

export function useUpdateMember(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, ...data }: { userId: string; is_reviewer?: boolean; role?: string }) =>
      api.patch(`/projects/${projectId}/members/${userId}`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-members', projectId] }),
  })
}

// ── Cache helpers ───────────────────────────────────────────────────────────

function setTask(qc: QueryClient, task: Task) {
  qc.setQueryData(['task', task.id], task)
  qc.setQueryData(['task-by-key', task.key], task)
  qc.invalidateQueries({ queryKey: ['tasks', task.project_id] })
}

function invalidateTask(qc: QueryClient, task: Task) {
  qc.invalidateQueries({ queryKey: ['task', task.id] })
  qc.invalidateQueries({ queryKey: ['task-by-key', task.key] })
  qc.invalidateQueries({ queryKey: ['tasks', task.project_id] })
  qc.invalidateQueries({ queryKey: ['task-history', task.id] })
}

function afterResultChange(qc: QueryClient, task: Task) {
  qc.invalidateQueries({ queryKey: ['proposals', task.id] })
  qc.invalidateQueries({ queryKey: ['review-queue'] })
  invalidateTask(qc, task)
}

/** Backend error code from an axios error, if any. */
export function errorCode(err: unknown): string | undefined {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return detail && typeof detail === 'object' && 'code' in detail ? String((detail as { code: string }).code) : undefined
}
