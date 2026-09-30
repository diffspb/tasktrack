import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, X } from 'lucide-react'
import { useDeleteTaskLink, useLinkTypes, useTaskLinks, type Task } from '../api'
import { LinkTaskDialog } from '../LinkTaskDialog'
import { TaskTypeIcon } from '../TaskTypeIcon'
import { TYPE_COLORS } from '../taskTypeColors'
import { SectionLabel } from './ui'

export function RelationsBlock({ task }: { task: Task }) {
  const { data: taskLinks = [] } = useTaskLinks(task.id)
  const { data: linkTypes = [] } = useLinkTypes()
  const deleteLink = useDeleteTaskLink(task.id, task.project_id)
  const [dialogOpen, setDialogOpen] = useState(false)

  const linkTypeMap = new Map(linkTypes.map(lt => [lt.id, lt]))
  // Tasks already linked are excluded from the search
  const linkedTaskIds = new Set([
    task.id,
    ...taskLinks.map(l => l.source_task.id),
    ...taskLinks.map(l => l.target_task.id),
  ])

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <SectionLabel>Relations</SectionLabel>
        <button
          onClick={() => setDialogOpen(true)}
          className="h-5 w-5 flex items-center justify-center rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          title="Add link"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>

      {taskLinks.length === 0 ? (
        <p className="text-sm text-muted-foreground italic">No relations.</p>
      ) : (
        <div className="space-y-1">
          {taskLinks.map(link => {
            const lt = linkTypeMap.get(link.link_type_id)
            const isSource = link.source_task.id === task.id
            const other    = isSource ? link.target_task : link.source_task
            const label    = lt ? (isSource ? lt.outward_name : lt.inward_name) : '→'
            const color    = lt?.color ?? '#6366f1'
            return (
              <div key={link.id} className="flex items-center gap-1.5 group">
                <span
                  className="text-[10px] font-medium shrink-0 px-1.5 py-0.5 rounded"
                  style={{ background: color + '22', color }}
                >
                  {label}
                </span>
                <TaskTypeIcon
                  typeKey={other.task_type?.key ?? 'task'}
                  color={other.task_type?.color ?? TYPE_COLORS[other.task_type?.key ?? 'task'] ?? '#6366f1'}
                  size={12}
                />
                <Link
                  to={`/tasks/${other.key}`}
                  className="font-mono text-[10px] text-muted-foreground hover:text-primary shrink-0"
                >
                  {other.key}
                </Link>
                <span className="text-xs text-foreground/80 truncate flex-1">{other.title}</span>
                <button
                  onClick={() => deleteLink.mutate(link.id)}
                  className="opacity-0 group-hover:opacity-100 text-muted-foreground/40 hover:text-destructive transition-opacity"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            )
          })}
        </div>
      )}

      <LinkTaskDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        taskId={task.id}
        projectId={task.project_id}
        excludeIds={linkedTaskIds}
      />
    </div>
  )
}
