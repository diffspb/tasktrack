import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export interface TaskType {
  id: string
  key: string
  name: string
  is_system: boolean
  color: string | null
  icon: string | null
}

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

export interface Resolution {
  id: string
  name: string
  is_default: boolean
  position: number
}

export type Priority = 'low' | 'medium' | 'high' | 'critical'

export interface Task {
  id: string
  key: string
  project_id: string
  workflow_id: string
  task_type_id: string
  task_type: TaskType | null
  reporter_id: string
  assignee_id: string | null
  parent_task_id: string | null
  current_status_id: string
  title: string
  description: string | null
  priority: Priority
  meta: Record<string, unknown>
  due_date: string | null
  version: number
  deleted_at: string | null
  created_at: string
  updated_at: string
}

export interface ProjectMember {
  user: { id: string; display_name: string; email: string }
  role: 'admin' | 'manager' | 'member' | 'viewer'
}

// --- Queries ---

export function useProjectTasks(projectId: string) {
  return useQuery<Task[]>({
    queryKey: ['tasks', projectId],
    queryFn: () => api.get(`/projects/${projectId}/tasks`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useTask(taskId: string | null | undefined) {
  return useQuery<Task>({
    queryKey: ['task', taskId],
    queryFn: () => api.get(`/tasks/${taskId}`).then(r => r.data),
    enabled: !!taskId,
  })
}

export function useTaskByKey(key: string | null | undefined) {
  return useQuery<Task>({
    queryKey: ['task-by-key', key],
    queryFn: () => api.get(`/tasks/by-key/${key}`).then(r => r.data),
    enabled: !!key,
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

export function useProjectMembers(projectId: string | null | undefined) {
  return useQuery<{ items: ProjectMember[] }>({
    queryKey: ['project-members', projectId],
    queryFn: () => api.get(`/projects/${projectId}/members`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useProjectTaskTypes(projectId: string | null | undefined) {
  return useQuery<TaskType[]>({
    queryKey: ['task-types', projectId],
    queryFn: () => api.get(`/projects/${projectId}/task-types`).then(r => r.data),
    enabled: !!projectId,
  })
}

// --- Mutations ---

export interface CreateTaskInput {
  title: string
  description?: string
  task_type_key?: string
  priority?: Priority
  assignee_id?: string
  due_date?: string
}

export function useCreateTask(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTaskInput) =>
      api.post(`/projects/${projectId}/tasks`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks', projectId] }),
  })
}

export interface UpdateTaskInput {
  title?: string
  description?: string
  priority?: Priority
  assignee_id?: string | null
  due_date?: string | null
  meta?: Record<string, unknown>
  version: number
}

export function useUpdateTask(taskId: string, projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdateTaskInput) =>
      api.patch(`/tasks/${taskId}`, data).then(r => r.data),
    onSuccess: (updated: Task) => {
      qc.invalidateQueries({ queryKey: ['tasks', projectId] })
      qc.setQueryData(['task', taskId], updated)
      qc.invalidateQueries({ queryKey: ['task-by-key', updated.key] })
    },
  })
}

export function useTransitionStatus(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, status_id, resolution_id }: { taskId: string; status_id: string; resolution_id?: string }) =>
      api.post(`/tasks/${taskId}/transition`, { status_id, resolution_id }).then(r => r.data),
    onSuccess: (updated: Task) => {
      qc.invalidateQueries({ queryKey: ['tasks', projectId] })
      qc.setQueryData(['task', updated.id], updated)
    },
  })
}

export function useDeleteTask(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => api.delete(`/tasks/${taskId}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks', projectId] }),
  })
}

// --- Comments ---

export interface Comment {
  id: string
  task_id: string
  author_id: string
  parent_comment_id: string | null
  content: string
  labels: string[]
  edited_at: string | null
  deleted_at: string | null
  created_at: string
  updated_at: string
}

export function useTaskComments(taskId: string | null | undefined) {
  return useQuery<Comment[]>({
    queryKey: ['comments', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/comments`).then(r => r.data),
    enabled: !!taskId,
  })
}

export function useCreateComment(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { content: string; labels?: string[] }) =>
      api.post(`/tasks/${taskId}/comments`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['comments', taskId] }),
  })
}

export function useUpdateComment(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ commentId, content }: { commentId: string; content: string }) =>
      api.patch(`/comments/${commentId}`, { content }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['comments', taskId] }),
  })
}

export function useDeleteComment(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (commentId: string) => api.delete(`/comments/${commentId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['comments', taskId] }),
  })
}
