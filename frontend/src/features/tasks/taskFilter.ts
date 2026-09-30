import type { Task, Priority } from './api'

export interface FilterState {
  assignee: 'all' | 'mine' | 'unassigned'
  priority: Priority | 'all'
  type: string  // 'all' or task type key
}

export const DEFAULT_FILTER: FilterState = {
  assignee: 'all',
  priority: 'all',
  type: 'all',
}

export function applyFilter(tasks: Task[], filter: FilterState, currentUserId: string): Task[] {
  return tasks.filter(t => {
    if (filter.assignee === 'mine' && t.assignee_id !== currentUserId) return false
    if (filter.assignee === 'unassigned' && t.assignee_id !== null) return false
    if (filter.priority !== 'all' && t.priority !== filter.priority) return false
    if (filter.type !== 'all' && (t.task_type?.key ?? 'task') !== filter.type) return false
    return true
  })
}
