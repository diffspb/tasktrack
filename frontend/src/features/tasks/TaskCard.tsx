import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import type { Task } from './api'
import { TaskTypeIcon } from './TaskTypeIcon'

const PRIORITY_COLORS: Record<string, string> = {
  low:      'oklch(0.65 0.08 240)',
  medium:   'oklch(0.55 0.14 200)',
  high:     'oklch(0.60 0.18 55)',
  critical: 'oklch(0.55 0.22 25)',
}

const TYPE_COLORS: Record<string, string> = {
  bug:      '#ef4444',
  story:    '#10b981',
  epic:     '#f59e0b',
  decision: '#8b5cf6',
  task:     '#6366f1',
}

interface Props {
  task: Task
  assigneeName?: string
  epicKey?: string
  isDragging: boolean
  onClick: () => void        // opens detail sheet
  onDragStart: () => void
  onDragEnd: () => void
}

export function TaskCard({ task, assigneeName, epicKey, isDragging, onClick, onDragStart, onDragEnd }: Props) {
  const priorityColor = PRIORITY_COLORS[task.priority] ?? PRIORITY_COLORS.medium
  const typeKey = task.task_type?.key ?? 'task'
  const typeColor = task.task_type?.color ?? TYPE_COLORS[typeKey] ?? TYPE_COLORS.task

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={cn(
        'relative cursor-pointer overflow-hidden rounded-lg border bg-card px-3 py-2.5 select-none',
        'transition-shadow hover:shadow-md hover:border-ring/40',
        isDragging && 'opacity-40',
      )}
    >
      <div className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-lg" style={{ background: priorityColor }} />

      <div className="pl-1.5 space-y-1.5">
        <div className="flex items-center gap-1.5">
          <TaskTypeIcon typeKey={typeKey} color={typeColor} size={13} />
          {/* Key is a link to the full task page — stops propagation to avoid opening sheet */}
          <Link
            to={`/tasks/${task.key}`}
            onClick={e => e.stopPropagation()}
            className="text-[11px] font-semibold text-muted-foreground hover:text-primary hover:underline transition-colors"
          >
            {task.key}
          </Link>
        </div>

        {epicKey && (
          <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400">{epicKey}</span>
        )}
        <p className="text-[13px] font-medium leading-snug line-clamp-2">{task.title}</p>

        <div className="flex items-center gap-2 pt-0.5">
          <span className="text-[11px] capitalize text-muted-foreground/60">{task.priority}</span>
          <div className="flex-1" />
          {assigneeName && (
            <span className="text-[11px] text-muted-foreground/60 max-w-[80px] truncate">
              {assigneeName}
            </span>
          )}
          {task.due_date && (
            <span className="text-[11px] text-muted-foreground/60">
              {new Date(task.due_date).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
