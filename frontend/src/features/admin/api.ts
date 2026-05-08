import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

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
  created_at: string
  updated_at: string
}

export interface LinkTypeCreate {
  name: string
  outward_name: string
  inward_name: string
  is_directed?: boolean
  color?: string | null
  constraint?: Record<string, unknown> | null
  position?: number
}

export interface LinkTypeUpdate {
  outward_name?: string
  inward_name?: string
  is_directed?: boolean
  color?: string | null
  constraint?: Record<string, unknown> | null
  position?: number
  is_active?: boolean
}

export function useLinkTypes(includeInactive = false) {
  return useQuery<LinkType[]>({
    queryKey: ['link-types', includeInactive],
    queryFn: () =>
      api.get('/link-types', { params: { include_inactive: includeInactive } }).then(r => r.data),
  })
}

export function useCreateLinkType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LinkTypeCreate) =>
      api.post('/link-types', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['link-types'] }),
  })
}

export function useUpdateLinkType(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LinkTypeUpdate) =>
      api.patch(`/link-types/${id}`, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['link-types'] }),
  })
}

export function useDeleteLinkType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/link-types/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['link-types'] }),
  })
}
