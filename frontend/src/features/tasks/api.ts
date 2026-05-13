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
  start_date: string | null
  due_date: string | null
  duration_days: number | null
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

export function useSearchTasks(q: string, typeKeys: string[] = []) {
  return useQuery<Task[]>({
    queryKey: ['tasks-search', q, typeKeys],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('q', q)
      typeKeys.forEach(k => params.append('task_type_keys', k))
      return api.get(`/tasks?${params}`).then(r => r.data)
    },
    enabled: q.length >= 1,
    staleTime: 30_000,
    placeholderData: prev => prev,
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

export function useProjectMembers(projectId: string | null | undefined) {
  return useQuery<{ items: ProjectMember[] }>({
    queryKey: ['project-members', projectId],
    queryFn: () => api.get(`/projects/${projectId}/members`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useTaskTypes() {
  return useQuery<{ items: TaskType[] }>({
    queryKey: ['task-types'],
    queryFn: () => api.get('/task-types').then(r => r.data),
    staleTime: 60_000,
  })
}

/** @deprecated use useTaskTypes() */
export function useProjectTaskTypes(_projectId?: string | null) {
  return useTaskTypes()
}

export function useChildTasks(projectId: string | null | undefined, parentTaskId: string | null | undefined) {
  return useQuery<Task[]>({
    queryKey: ['child-tasks', projectId, parentTaskId],
    queryFn: () =>
      api.get(`/projects/${projectId}/tasks?parent_task_id=${parentTaskId}`).then(r => r.data),
    enabled: !!projectId && !!parentTaskId,
  })
}

export function useProjectEpics(projectId: string | null | undefined) {
  return useQuery<Task[]>({
    queryKey: ['epics', projectId],
    queryFn: () =>
      api.get(`/projects/${projectId}/tasks?task_type_key=epic`).then(r => r.data),
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
  parent_task_id?: string
  due_date?: string
}

export function useCreateTask(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTaskInput) =>
      api.post(`/projects/${projectId}/tasks`, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks', projectId] })
      qc.invalidateQueries({ queryKey: ['child-tasks', projectId] })
    },
  })
}

export interface UpdateTaskInput {
  title?: string
  description?: string
  priority?: Priority
  assignee_id?: string | null
  start_date?: string | null
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
      qc.invalidateQueries({ queryKey: ['gantt-tasks'] })
    },
  })
}

export function useTransitionStatus(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ taskId, status_id }: { taskId: string; status_id: string }) =>
      api.post(`/tasks/${taskId}/transition`, { status_id }).then(r => r.data),
    onMutate: async ({ taskId, status_id }) => {
      await qc.cancelQueries({ queryKey: ['tasks', projectId] })
      const previous = qc.getQueryData<Task[]>(['tasks', projectId])
      qc.setQueryData<Task[]>(['tasks', projectId], old =>
        old?.map(t => t.id === taskId ? { ...t, current_status_id: status_id } : t)
      )
      return { previous }
    },
    onSuccess: (updated: Task) => {
      qc.setQueryData<Task[]>(['tasks', projectId], old =>
        old?.map(t => t.id === updated.id ? updated : t)
      )
      qc.setQueryData(['task', updated.id], updated)
      qc.setQueryData(['task-by-key', updated.key], updated)
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        qc.setQueryData(['tasks', projectId], context.previous)
      }
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

// --- Link Types ---

export interface LinkType {
  id: string
  name: string
  outward_name: string
  inward_name: string
  is_directed: boolean
  color: string | null
  constraint: Record<string, unknown> | null
  position: number
  is_active: boolean
}

export function useLinkTypes() {
  return useQuery<LinkType[]>({
    queryKey: ['link-types'],
    queryFn: () => api.get('/link-types').then(r => r.data),
    staleTime: 5 * 60_000,
  })
}

// --- Task Links ---

export interface TaskLinkTask {
  id: string
  key: string
  title: string
  task_type: TaskType | null
}

export interface TaskLink {
  id: string
  source_task: TaskLinkTask
  target_task: TaskLinkTask
  link_type_id: string
  link_type: LinkType
  created_at: string
}

export function useTaskLinks(taskId: string | null | undefined) {
  return useQuery<TaskLink[]>({
    queryKey: ['task-links', taskId],
    queryFn: () => api.get(`/tasks/${taskId}/links`).then(r => r.data),
    enabled: !!taskId,
  })
}

export function useCreateTaskLink(viewTaskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { source_task_id: string; target_task_id: string; link_type_id: string }) =>
      api.post(`/tasks/${data.source_task_id}/links`, {
        target_task_id: data.target_task_id,
        link_type_id: data.link_type_id,
      }).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['task-links', viewTaskId] })
      qc.invalidateQueries({ queryKey: ['gantt-tasks'] })
      qc.invalidateQueries({ queryKey: ['gantt-links'] })
    },
  })
}

export function useDeleteTaskLink(taskId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (linkId: string) => api.delete(`/tasks/${taskId}/links/${linkId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['task-links', taskId] })
      qc.invalidateQueries({ queryKey: ['gantt-tasks'] })
      qc.invalidateQueries({ queryKey: ['gantt-links'] })
    },
  })
}
