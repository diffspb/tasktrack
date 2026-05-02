import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export type StatusCategory = 'initial' | 'intermediate' | 'final'

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
      position?: number
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
