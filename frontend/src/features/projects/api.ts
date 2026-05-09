import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export interface ProjectMember {
  user_id: string
  role: string
}

export interface Project {
  id: string
  name: string
  key: string
  description: string | null
  visibility: 'public' | 'restricted' | 'private'
  is_archived: boolean
  version: number
  members: ProjectMember[]
  created_at: string
}

export interface ProjectCreate {
  name: string
  key: string
  description?: string
  visibility?: 'public' | 'restricted' | 'private'
}

export function useProjects() {
  return useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: () => api.get('/projects').then(r => r.data),
  })
}

export function useProject(projectId: string | null | undefined) {
  return useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: () => api.get(`/projects/${projectId}`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useProjectByKey(key: string | null | undefined) {
  return useQuery<Project>({
    queryKey: ['project-by-key', key?.toUpperCase()],
    queryFn: () => api.get(`/projects/by-key/${key}`).then(r => r.data),
    enabled: !!key,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: ProjectCreate) => api.post('/projects', data).then(r => r.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export interface ProjectUpdate {
  name?: string
  description?: string | null
  visibility?: Project['visibility']
  version: number
}

export function useUpdateProject(projectId: string | undefined) {
  const qc = useQueryClient()
  return useMutation<Project, unknown, ProjectUpdate>({
    mutationFn: data => api.patch(`/projects/${projectId}`, data).then(r => r.data),
    onSuccess: updated => {
      qc.setQueryData(['project', projectId], updated)
      qc.setQueryData(['project-by-key', updated.key.toUpperCase()], updated)
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useArchiveProject(projectId: string | undefined) {
  const qc = useQueryClient()
  return useMutation<Project>({
    mutationFn: () => api.post(`/projects/${projectId}/archive`).then(r => r.data),
    onSuccess: updated => {
      qc.setQueryData(['project', projectId], updated)
      qc.setQueryData(['project-by-key', updated.key.toUpperCase()], updated)
      qc.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export async function downloadProjectExport(projectId: string, projectKey: string): Promise<void> {
  const response = await api.get(`/projects/${projectId}/export`, { responseType: 'blob' })
  const blob = new Blob([response.data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${projectKey}-export.json`
  a.click()
  URL.revokeObjectURL(url)
}

export interface ProjectImportPayload {
  data: Record<string, unknown>
  new_key: string
  include_comments: boolean
  reset_statuses: boolean
}

export function useImportProject() {
  const qc = useQueryClient()
  return useMutation<Project, unknown, ProjectImportPayload>({
    mutationFn: payload => api.post('/projects/import', payload).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}
