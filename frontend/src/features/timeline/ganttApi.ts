import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import type { Task } from '@/features/tasks/api'

export interface GanttChart {
  id: string
  owner_id: string
  name: string
  description: string | null
  settings: Record<string, unknown>
  position: number
  created_at: string
  updated_at: string
}

export function useGanttCharts() {
  return useQuery<GanttChart[]>({
    queryKey: ['gantt-charts'],
    queryFn: () => api.get('/gantt').then(r => r.data),
  })
}

export function useGanttChart(id: string | null | undefined) {
  return useQuery<GanttChart>({
    queryKey: ['gantt-chart', id],
    queryFn: () => api.get(`/gantt/${id}`).then(r => r.data),
    enabled: !!id,
  })
}

export function useGanttTasks(ganttId: string | null | undefined) {
  return useQuery<Task[]>({
    queryKey: ['gantt-tasks', ganttId],
    queryFn: () => api.get(`/gantt/${ganttId}/tasks`).then(r => r.data),
    enabled: !!ganttId,
  })
}

export function useCreateGanttChart() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      api.post('/gantt', data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gantt-charts'] }),
  })
}

export function useUpdateGanttChart(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name?: string; description?: string; settings?: Record<string, unknown> }) =>
      api.patch(`/gantt/${id}`, data).then(r => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['gantt-charts'] })
      qc.invalidateQueries({ queryKey: ['gantt-chart', id] })
    },
  })
}

export function useDeleteGanttChart() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/gantt/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gantt-charts'] }),
  })
}

export function useAddTaskToGantt(ganttId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) =>
      api.post(`/gantt/${ganttId}/tasks`, { task_id: taskId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gantt-tasks', ganttId] }),
  })
}

export function useRemoveTaskFromGantt(ganttId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (taskId: string) => api.delete(`/gantt/${ganttId}/tasks/${taskId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['gantt-tasks', ganttId] }),
  })
}
