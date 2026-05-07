import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export interface View {
  id: string
  project_id: string
  name: string
  type: 'kanban' | 'backlog' | 'epic_tree'
  position: number
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface ViewCreate {
  name: string
  type: View['type']
  position?: number
}

export interface ViewUpdate {
  name?: string
  position?: number
}

export function useProjectViews(projectId: string | null | undefined) {
  return useQuery<View[]>({
    queryKey: ['views', projectId],
    queryFn: () => api.get(`/projects/${projectId}/views`).then(r => r.data),
    enabled: !!projectId,
  })
}

export function useView(viewId: string | null | undefined) {
  return useQuery<View>({
    queryKey: ['view', viewId],
    queryFn: () => api.get(`/views/${viewId}`).then(r => r.data),
    enabled: !!viewId,
  })
}

export function useCreateView(projectId: string | undefined) {
  const qc = useQueryClient()
  return useMutation<View, unknown, ViewCreate>({
    mutationFn: data => api.post(`/projects/${projectId}/views`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['views', projectId] }),
  })
}

export function useUpdateView(viewId: string | undefined, projectId: string | undefined) {
  const qc = useQueryClient()
  return useMutation<View, unknown, ViewUpdate>({
    mutationFn: data => api.patch(`/views/${viewId}`, data).then(r => r.data),
    onSuccess: updated => {
      qc.setQueryData(['view', viewId], updated)
      qc.invalidateQueries({ queryKey: ['views', projectId] })
    },
  })
}

export function useDeleteView(projectId: string | undefined) {
  const qc = useQueryClient()
  return useMutation<void, unknown, string>({
    mutationFn: (viewId: string) => api.delete(`/views/${viewId}`).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['views', projectId] }),
  })
}
