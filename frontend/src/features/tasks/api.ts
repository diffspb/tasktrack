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

export interface Assignment {
  id: string
  task_id: string
  user_id: string
  role: 'lead' | 'reviewer' | 'consultant'
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
  version: number
  assignments: Assignment[]
  created_at: string
  updated_at: string
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
}

export function useCreateTask(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTaskInput) =>
      api.post(`/projects/${projectId}/tasks`, data).then(r => r.data),
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
