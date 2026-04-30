import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export interface Status {
  id: string
  name: string
  category: 'initial' | 'intermediate' | 'final'
  is_default: boolean
  position: number
  color: string | null
}

export interface Transition {
  id: string
  from_status_id: string
  to_status_id: string
}

export interface Workflow {
  id: string
  name: string
  is_default: boolean
  statuses: Status[]
  transitions: Transition[]
  created_at: string
}

export type AssigneeRole = 'lead' | 'reviewer' | 'consultant'

export interface Assignment {
  id: string
  task_id: string
  user_id: string
  role: AssigneeRole
  current_status_id: string
  resolution_id: string | null
  created_at: string
}

export type GlobalStatus =
  | 'open' | 'in_progress' | 'awaiting_decision'
  | 'in_revision' | 'decided' | 'closed'

export type Priority = 'low' | 'medium' | 'high' | 'critical'

export interface Task {
  id: string
  project_id: string
  workflow_id: string
  key: string
  title: string
  description: string | null
  task_type: string
  priority: Priority
  global_status: GlobalStatus
  reporter_id: string
  decision_maker_id: string | null
  due_date: string | null
  allow_multi_accept: boolean
  version: number
  assignments: Assignment[]
  created_at: string
  updated_at: string
}

export type SolutionStatus = 'draft' | 'submitted' | 'accepted' | 'revision_requested'

export interface Solution {
  id: string
  assignment_id: string
  content: string
  status: SolutionStatus
  submitted_at: string | null
  revision_comment: string | null
  created_at: string
  updated_at: string
}

export interface DecisionCriteria {
  id: string
  description: string
  position: number
  is_locked: boolean
}

export interface TaskDecision {
  id: string
  task_id: string
  decision_maker_id: string
  accepted_solution_ids: string[]
  note: string | null
  decided_at: string
}

export interface Resolution {
  id: string
  name: string
  is_default: boolean
  position: number
}

export function useProjectTasks(projectId: string) {
  return useQuery<Task[]>({
    queryKey: ['tasks', projectId],
    queryFn: () => api.get(`/projects/${projectId}/tasks`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useProjectWorkflows(projectId: string) {
  return useQuery<Workflow[]>({
    queryKey: ['workflows', projectId],
    queryFn: () => api.get(`/projects/${projectId}/workflows`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useProjectResolutions(projectId: string) {
  return useQuery<Resolution[]>({
    queryKey: ['resolutions', projectId],
    queryFn: () => api.get(`/projects/${projectId}/resolutions`).then(r => r.data),
    enabled: !!projectId,
  })
}

export interface CreateTaskInput {
  title: string
  workflow_id: string
  priority?: Priority
  description?: string
  decision_maker_id?: string
  allow_multi_accept?: boolean
}

export function useCreateTask(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTaskInput) =>
      api.post(`/projects/${projectId}/tasks`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks', projectId] }),
  })
}

export function useAssignUser(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, userId, role }: { taskId: string; userId: string; role: string }) =>
      api.post(`/tasks/${taskId}/assignments`, { user_id: userId, role }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks', projectId] }),
  })
}

export function useTransitionStatus(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assignmentId, ...data }: { assignmentId: string; status_id: string; resolution_id?: string }) =>
      api.patch(`/assignments/${assignmentId}/status`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks', projectId] }),
  })
}

// --- Decision Process ----------------------------------------------------

export function useTaskSolutions(taskId: string | null | undefined) {
  return useQuery<Solution[]>({
    queryKey: ['solutions', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/solutions`).then(r => r.data),
    enabled: !!taskId,
  })
}

export function useAssignmentSolution(assignmentId: string | null | undefined) {
  return useQuery<Solution | null>({
    queryKey: ['assignment-solution', assignmentId],
    queryFn: () =>
      api
        .get(`/assignments/${assignmentId}/solution`)
        .then(r => r.data)
        .catch(err => {
          if (err?.response?.status === 404) return null
          throw err
        }),
    enabled: !!assignmentId,
  })
}

function invalidateTaskQueries(qc: ReturnType<typeof useQueryClient>, projectId: string, taskId: string) {
  qc.invalidateQueries({ queryKey: ['tasks', projectId] })
  qc.invalidateQueries({ queryKey: ['solutions', taskId] })
  qc.invalidateQueries({ queryKey: ['decision', taskId] })
  qc.invalidateQueries({ queryKey: ['decision-criteria', taskId] })
  qc.invalidateQueries({ queryKey: ['assignment-solution'] })
}

export function useCreateSolution(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ assignmentId, content }: { assignmentId: string; content: string }) =>
      api.post(`/assignments/${assignmentId}/solution`, { content }).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

export function useUpdateSolution(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ solutionId, content }: { solutionId: string; content: string }) =>
      api.patch(`/solutions/${solutionId}`, { content }).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

export function useSubmitSolution(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (solutionId: string) =>
      api.post(`/solutions/${solutionId}/submit`).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

export function useWithdrawSolution(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (solutionId: string) =>
      api.post(`/solutions/${solutionId}/withdraw`).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

export function useRequestRevision(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ solutionId, feedback }: { solutionId: string; feedback: string }) =>
      api.post(`/solutions/${solutionId}/request-revision`, { feedback }).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

export function useDecisionCriteria(taskId: string | null | undefined) {
  return useQuery<{ items: DecisionCriteria[] }>({
    queryKey: ['decision-criteria', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/decision-criteria`).then(r => r.data),
    enabled: !!taskId,
  })
}

export function useReplaceCriteria(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (items: { description: string; position: number }[]) =>
      api.put(`/tasks/${taskId}/decision-criteria`, { items }).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

export function useDecision(taskId: string | null | undefined) {
  return useQuery<TaskDecision | null>({
    queryKey: ['decision', taskId],
    queryFn: () =>
      api
        .get(`/tasks/${taskId}/decisions`)
        .then(r => r.data)
        .catch(err => {
          if (err?.response?.status === 404) return null
          throw err
        }),
    enabled: !!taskId,
  })
}

export function useMakeDecision(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ accepted_solution_ids, note }: { accepted_solution_ids: string[]; note?: string }) =>
      api.post(`/tasks/${taskId}/decisions`, { accepted_solution_ids, note }).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

export function useCloseTask(projectId: string, taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post(`/tasks/${taskId}/close`).then(r => r.data),
    onSuccess: () => invalidateTaskQueries(qc, projectId, taskId),
  })
}

// --- Project members (for assignee picker / DM picker) ----------------

export interface ProjectMember {
  user: { id: string; display_name: string; email: string }
  role: 'admin' | 'manager' | 'member' | 'viewer'
}

export function useProjectMembers(projectId: string | null | undefined) {
  return useQuery<{ items: ProjectMember[] }>({
    queryKey: ['project-members', projectId],
    queryFn: () => api.get(`/projects/${projectId}/members`).then(r => r.data),
    enabled: !!projectId,
  })
}
