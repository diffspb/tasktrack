import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

export type NotificationEventType =
  | 'task_assigned' | 'awaiting_decision' | 'revision_requested'
  | 'decision_made' | 'task_closed' | 'decision_reminder'

export interface Notification {
  id: string
  event_type: NotificationEventType
  entity_type: 'task' | 'solution'
  entity_id: string
  task_id: string | null
  message: string
  is_read: boolean
  created_at: string
}

export interface NotificationListResponse {
  total: number
  unread_count: number
  items: Notification[]
}

export function useNotifications(opts?: { onlyUnread?: boolean; refetchInterval?: number }) {
  const params = opts?.onlyUnread ? '?is_read=false' : ''
  return useQuery<NotificationListResponse>({
    queryKey: ['notifications', opts?.onlyUnread ?? false],
    queryFn: () => api.get(`/notifications${params}`).then(r => r.data),
    refetchInterval: opts?.refetchInterval ?? 30_000,
  })
}

export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.patch(`/notifications/${id}`, { is_read: true }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}

export function useMarkAllRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/notifications/read-all'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['notifications'] }),
  })
}
