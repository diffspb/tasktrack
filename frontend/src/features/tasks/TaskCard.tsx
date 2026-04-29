import { cn } from '@/lib/utils'
import type { Task, Assignment } from './api'

const PRIORITY_COLORS: Record<string, string> = {
  low:      'oklch(0.65 0.08 240)',
  medium:   'oklch(0.55 0.14 200)',
  high:     'oklch(0.60 0.18 55)',
  critical: 'oklch(0.55 0.22 25)',
}

const GLOBAL_STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  open:              { bg: 'bg-muted',                                          text: 'text-muted-foreground',                 label: 'Open' },
  in_progress:       { bg: 'bg-blue-100 dark:bg-blue-900/30',                   text: 'text-blue-700 dark:text-blue-300',       label: 'In Progress' },
  awaiting_decision: { bg: 'bg-yellow-100 dark:bg-yellow-900/30',               text: 'text-yellow-700 dark:text-yellow-300',   label: 'Awaiting' },
  in_revision:       { bg: 'bg-orange-100 dark:bg-orange-900/30',               text: 'text-orange-700 dark:text-orange-300',   label: 'Revision' },
  decided:           { bg: 'bg-green-100 dark:bg-green-900/30',                 text: 'text-green-700 dark:text-green-300',     label: 'Decided' },
  closed:            { bg: 'bg-muted',                                          text: 'text-muted-foreground',                  label: 'Closed' },
}

interface Props {
  task: Task
  myAssignment: Assignment | undefined
  statusName: string
  isDragging: boolean
  onClick: () => void
  onDragStart: () => void
  onDragEnd: () => void
}

export function TaskCard({ task, isDragging, onClick, onDragStart, onDragEnd }: Props) {
  const gs = GLOBAL_STATUS_STYLES[task.global_status] ?? GLOBAL_STATUS_STYLES.open
  const priorityColor = PRIORITY_COLORS[task.priority] ?? PRIORITY_COLORS.medium
  const multiLead = task.assignments.filter(a => a.role === 'lead').length > 1

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={cn(
        'relative cursor-grab overflow-hidden rounded-lg border bg-card px-3 py-2.5 select-none',
        'transition-shadow hover:shadow-md hover:border-ring/40',
        isDragging && 'opacity-40 cursor-grabbing',
      )}
    >
      <div className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-lg" style={{ background: priorityColor }} />

      <div className="pl-1.5 space-y-1.5">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[11px] font-semibold text-muted-foreground/70">{task.key}</span>
          <div className="flex-1" />
          <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium', gs.bg, gs.text)}>
            {gs.label}
          </span>
        </div>

        <p className="text-[13px] font-medium leading-snug line-clamp-2">{task.title}</p>

        <div className="flex items-center gap-2 pt-0.5">
          <span className="text-[11px] capitalize text-muted-foreground/60">{task.priority}</span>
          {multiLead && (
            <span className="text-[10px] text-muted-foreground/60 bg-muted rounded px-1">
              {task.assignments.filter(a => a.role === 'lead').length} leads
            </span>
          )}
          <div className="flex-1" />
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
