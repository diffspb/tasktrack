import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import type { Task, Status } from './api'
import { TaskView } from './TaskView'
import { TaskTypeIcon } from './TaskTypeIcon'

interface Props {
  task: Task | null
  statuses?: Status[]
  transitions?: { from_status_id: string; to_status_id: string }[]
  projectId: string
  currentUserId: string
  onClose: () => void
}

export function TaskDetail({ task, currentUserId, onClose }: Props) {
  if (!task) return null

  const typeKey = task.task_type?.key ?? 'task'

  return (
    <div className="w-[460px] shrink-0 border-l bg-background flex flex-col overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center gap-2 border-b px-4 py-2.5 shrink-0">
        <TaskTypeIcon typeKey={typeKey} color={task.task_type?.color} size={14} />
        <Link
          to={`/tasks/${task.key}`}
          className="text-xs font-semibold text-muted-foreground hover:text-primary hover:underline transition-colors"
        >
          {task.key}
        </Link>
        <div className="flex-1" />
        <button
          onClick={onClose}
          className="rounded p-1 text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <TaskView task={task} mode="panel" currentUserId={currentUserId} />
    </div>
  )
}
