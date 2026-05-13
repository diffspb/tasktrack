import type { Task, Priority } from './api'
import { useProjectTaskTypes } from './api'

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

const PRIORITIES: { value: Priority | 'all'; label: string }[] = [
  { value: 'all',      label: 'All priorities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high',     label: 'High' },
  { value: 'medium',   label: 'Medium' },
  { value: 'low',      label: 'Low' },
]

const ASSIGNEE_OPTS = [
  { value: 'all' as const,       label: 'Everyone' },
  { value: 'mine' as const,      label: 'Mine' },
  { value: 'unassigned' as const, label: 'Unassigned' },
]

interface Props {
  filter: FilterState
  onChange: (f: FilterState) => void
  taskCount: number
  projectId: string
}

export function TaskFilterBar({ filter, onChange, taskCount, projectId }: Props) {
  const { data: taskTypesData } = useProjectTaskTypes(projectId)
  const taskTypes = taskTypesData?.items ?? []
  const active =
    filter.assignee !== 'all' || filter.priority !== 'all' || filter.type !== 'all'

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* Assignee */}
      <div className="flex items-center gap-0.5 rounded-md border bg-background">
        {ASSIGNEE_OPTS.map(opt => (
          <button
            key={opt.value}
            onClick={() => onChange({ ...filter, assignee: opt.value })}
            className={`px-2.5 py-1 text-xs rounded-[5px] transition-colors ${
              filter.assignee === opt.value
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground hover:bg-muted'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Priority */}
      <select
        value={filter.priority}
        onChange={e => onChange({ ...filter, priority: e.target.value as FilterState['priority'] })}
        className="h-7 rounded-md border border-input bg-background px-2 text-xs text-muted-foreground"
      >
        {PRIORITIES.map(p => (
          <option key={p.value} value={p.value}>{p.label}</option>
        ))}
      </select>

      {/* Type */}
      <select
        value={filter.type}
        onChange={e => onChange({ ...filter, type: e.target.value })}
        className="h-7 rounded-md border border-input bg-background px-2 text-xs text-muted-foreground"
      >
        <option value="all">All types</option>
        {taskTypes.map(t => (
          <option key={t.key} value={t.key}>{t.name}</option>
        ))}
      </select>

      <span className="text-xs text-muted-foreground ml-1">{taskCount} tasks</span>

      {active && (
        <button
          onClick={() => onChange(DEFAULT_FILTER)}
          className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2"
        >
          Clear
        </button>
      )}
    </div>
  )
}
