import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import type { Task } from '@/features/tasks/api'

export function useGlobalTasks(projectIds?: string[]) {
  const params = projectIds?.length
    ? '?' + projectIds.map(id => `project_ids=${id}`).join('&')
    : ''
  return useQuery<Task[]>({
    queryKey: ['global-tasks', projectIds ?? []],
    queryFn: () => api.get(`/tasks${params}`).then(r => r.data),
  })
}
