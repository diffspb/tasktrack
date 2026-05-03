import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export type StatusCategory = 'initial' | 'intermediate' | 'final'

// ── Board columns ─────────────────────────────────────────────────────────────

export interface BoardColumn {
  id: string
  project_id: string
  name: string
  position: number
  status_ids: string[]
  created_at: string
  updated_at: string
}

// ── Task type configs ─────────────────────────────────────────────────────────

export interface TaskTypeConfig {
  task_type_id: string
  task_type_key: string
  task_type_name: string
  workflow_id: string | null
  workflow_name: string | null
  is_project_override: boolean
}

export interface WorkflowStatus {
  id: string
  workflow_id: string
  name: string
  category: StatusCategory
  is_default: boolean
  position: number
  color: string | null
  created_at: string
  updated_at: string
}

export interface WorkflowTransition {
  id: string
  workflow_id: string
  from_status_id: string
  to_status_id: string
  required_role: string | null
}

export interface Workflow {
  id: string
  project_id: string
  name: string
  is_default: boolean
  statuses: WorkflowStatus[]
  transitions: WorkflowTransition[]
  created_at: string
  updated_at: string
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useProjectWorkflows(projectId: string | undefined) {
  return useQuery<Workflow[]>({
    queryKey: ['workflows', projectId],
    queryFn: () => api.get(`/projects/${projectId}/workflows`).then(r => r.data),
    enabled: !!projectId,
  })
}

// ── Workflow mutations ────────────────────────────────────────────────────────

export function useUpdateWorkflow(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ workflowId, name }: { workflowId: string; name: string }) =>
      api.patch(`/workflows/${workflowId}`, { name }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

// ── Status mutations ──────────────────────────────────────────────────────────

export function useCreateStatus(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ workflowId, ...data }: {
      workflowId: string
      name: string
      category: StatusCategory
      position: number
      color?: string
      is_default?: boolean
    }) => api.post(`/workflows/${workflowId}/statuses`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

export function useUpdateStatus(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ statusId, ...data }: {
      statusId: string
      name?: string
      category?: StatusCategory
      position?: number
      is_default?: boolean
      color?: string
    }) => api.patch(`/statuses/${statusId}`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

export function useDeleteStatus(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (statusId: string) => api.delete(`/statuses/${statusId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

export function useMigrateStatus(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ statusId, targetStatusId }: { statusId: string; targetStatusId: string }) =>
      api.post(`/statuses/${statusId}/migrate`, { target_status_id: targetStatusId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflows', projectId] })
      qc.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}

// ── Transition mutations ──────────────────────────────────────────────────────

export function useCreateTransition(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ workflowId, from_status_id, to_status_id }: {
      workflowId: string
      from_status_id: string
      to_status_id: string
    }) => api.post(`/workflows/${workflowId}/transitions`, { from_status_id, to_status_id }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

export function useDeleteTransition(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (transitionId: string) => api.delete(`/transitions/${transitionId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

// ── Workflow create/delete ────────────────────────────────────────────────────

export function useCreateWorkflow(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      api.post(`/projects/${projectId}/workflows`, { name }).then(r => r.data as Workflow),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

export function useDeleteWorkflow(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (workflowId: string) => api.delete(`/workflows/${workflowId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', projectId] }),
  })
}

// ── Board columns ─────────────────────────────────────────────────────────────

export function useBoardColumns(projectId: string | undefined) {
  return useQuery<{ items: BoardColumn[] }>({
    queryKey: ['board-columns', projectId],
    queryFn: () => api.get(`/projects/${projectId}/board-columns`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useCreateBoardColumn(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, position }: { name: string; position: number }) =>
      api.post(`/projects/${projectId}/board-columns`, { name, position }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board-columns', projectId] }),
  })
}

export function useUpdateBoardColumn(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ columnId, name, position }: { columnId: string; name?: string; position?: number }) =>
      api.patch(`/board-columns/${columnId}`, { name, position }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board-columns', projectId] }),
  })
}

export function useDeleteBoardColumn(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (columnId: string) => api.delete(`/board-columns/${columnId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board-columns', projectId] }),
  })
}

export function useAddStatusToColumn(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ columnId, statusId }: { columnId: string; statusId: string }) =>
      api.post(`/board-columns/${columnId}/statuses`, { status_id: statusId }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board-columns', projectId] }),
  })
}

export function useRemoveStatusFromColumn(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ columnId, statusId }: { columnId: string; statusId: string }) =>
      api.delete(`/board-columns/${columnId}/statuses/${statusId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['board-columns', projectId] }),
  })
}

// ── Task type configs ─────────────────────────────────────────────────────────

export function useTaskTypeConfigs(projectId: string | undefined) {
  return useQuery<{ items: TaskTypeConfig[] }>({
    queryKey: ['task-type-configs', projectId],
    queryFn: () => api.get(`/projects/${projectId}/task-type-configs`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useSetTaskTypeWorkflow(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ taskTypeId, workflowId }: { taskTypeId: string; workflowId: string }) =>
      api.put(`/projects/${projectId}/task-type-configs/${taskTypeId}`, { workflow_id: workflowId }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['task-type-configs', projectId] }),
  })
}

export function useResetTaskTypeWorkflow(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskTypeId: string) =>
      api.delete(`/projects/${projectId}/task-type-configs/${taskTypeId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['task-type-configs', projectId] }),
  })
}
