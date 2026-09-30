import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTask, useUpdateTask, type Priority, type Status, type Task } from '../api'
import { TaskTypeIcon } from '../TaskTypeIcon'
import { TYPE_COLORS } from '../taskTypeColors'
import { PRIORITY_CONFIG, STATUS_DOT } from './constants'
import { SectionLabel } from './ui'

export function DetailsBlock({ task, currentStatus }: { task: Task; currentStatus?: Status }) {
  const updateTask = useUpdateTask(task.id, task.project_id)
  const { data: parentTask } = useTask(task.parent_task_id)
  const [editingPriority, setEditingPriority] = useState(false)

  const typeKey = task.task_type?.key ?? 'task'
  const typeColor = task.task_type?.color ?? TYPE_COLORS[typeKey] ?? TYPE_COLORS.task
  const { Icon: PriorityIcon, color: priorityColor } = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium

  return (
    <div className="space-y-2">
      <SectionLabel>Details</SectionLabel>
      <div className="space-y-0.5 text-sm">
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Type</span>
          <TaskTypeIcon typeKey={typeKey} color={typeColor} size={13} />
          <span className="capitalize">{task.task_type?.name ?? typeKey}</span>
        </div>
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Priority</span>
          {editingPriority ? (
            <select
              autoFocus
              defaultValue={task.priority}
              onChange={async e => {
                const val = e.target.value as Priority
                setEditingPriority(false)
                if (val !== task.priority)
                  await updateTask.mutateAsync({ priority: val, version: task.version })
              }}
              onBlur={() => setEditingPriority(false)}
              className="text-sm bg-background border border-input rounded px-1.5 py-0.5 outline-none focus:border-primary capitalize"
            >
              {(['low', 'medium', 'high', 'critical'] as const).map(p => (
                <option key={p} value={p} className="capitalize">{p}</option>
              ))}
            </select>
          ) : (
            <button
              onClick={() => setEditingPriority(true)}
              className="flex items-center gap-1.5 rounded px-1 -mx-1 hover:bg-muted/40 transition-colors"
            >
              <PriorityIcon size={13} style={{ color: priorityColor, flexShrink: 0 }} />
              <span className="text-sm capitalize">{task.priority}</span>
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Status</span>
          <div
            className="h-2 w-2 rounded-full shrink-0"
            style={{ background: STATUS_DOT[currentStatus?.category ?? 'initial'] }}
          />
          <span>{currentStatus?.name ?? '—'}</span>
        </div>
        {parentTask && (
          <div className="flex items-center gap-2 py-1.5">
            <span className="text-[11px] text-muted-foreground w-20 shrink-0">Parent</span>
            <Link
              to={`/tasks/${parentTask.key}`}
              className="flex items-center gap-1.5 hover:underline min-w-0"
            >
              <TaskTypeIcon typeKey={parentTask.task_type?.key ?? 'task'} color={parentTask.task_type?.color} size={12} />
              <span className="font-medium shrink-0">{parentTask.key}</span>
              <span className="text-muted-foreground truncate">{parentTask.title}</span>
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
