import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useChildTasks, type Status, type Task } from '../api'
import { CreateTaskModal } from '../CreateTaskModal'
import { TaskTypeIcon } from '../TaskTypeIcon'
import { SectionLabel } from './ui'

/** Subtasks with their statuses — from any workflow, subtasks may be process tasks (ADR-023). */
export function ChildTasks({ task, statuses }: { task: Task; statuses: Status[] }) {
  const { data: childTasks = [] } = useChildTasks(task.project_id, task.id)
  const [createOpen, setCreateOpen] = useState(false)
  const children = childTasks.filter(t => !t.deleted_at)

  return (
    <>
      {children.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <SectionLabel>Child tasks ({children.length})</SectionLabel>
            <button
              onClick={() => setCreateOpen(true)}
              className="ml-auto p-0.5 rounded text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
              title="Add child task"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <line x1="7" y1="2" x2="7" y2="12" /><line x1="2" y1="7" x2="12" y2="7" />
              </svg>
            </button>
          </div>
          <ul className="rounded-lg border divide-y text-sm">
            {children.map(child => {
              const cs = statuses.find(s => s.id === child.current_status_id)
              const cls =
                cs?.category === 'final'   ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                cs?.category === 'initial' ? 'bg-muted text-muted-foreground' :
                'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
              return (
                <li key={child.id}>
                  <Link
                    to={`/tasks/${child.key}`}
                    className="flex items-center gap-2.5 px-3 py-2 hover:bg-muted/50 transition-colors group"
                  >
                    <TaskTypeIcon typeKey={child.task_type?.key ?? 'task'} color={child.task_type?.color} size={12} />
                    <span className="text-[11px] font-semibold text-muted-foreground group-hover:text-primary transition-colors shrink-0 w-16">
                      {child.key}
                    </span>
                    <span className="flex-1 truncate">{child.title}</span>
                    {cs && (
                      <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium shrink-0 ${cls}`}>
                        {cs.name}
                      </span>
                    )}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      )}
      <CreateTaskModal
        open={createOpen}
        projectId={task.project_id}
        parentTaskId={task.id}
        onClose={() => setCreateOpen(false)}
      />
    </>
  )
}
