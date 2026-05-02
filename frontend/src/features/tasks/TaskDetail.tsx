import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import type { Task, Status, Resolution } from './api'
import { TaskView } from './TaskView'

interface Props {
  task: Task | null
  // statuses/transitions/resolutions kept for API compat with Board/Backlog
  // (TaskView fetches them internally, but callers still pass them — ignored here)
  statuses?: Status[]
  transitions?: { from_status_id: string; to_status_id: string }[]
  resolutions?: Resolution[]
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
        <Link
          to={`/tasks/${task.key}`}
          className="font-mono text-xs font-semibold text-muted-foreground hover:text-primary hover:underline transition-colors"
        >
          {task.key}
        </Link>
        <span className="text-xs text-muted-foreground/50 capitalize bg-muted rounded px-1.5 py-0.5">
          {typeKey}
        </span>
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
