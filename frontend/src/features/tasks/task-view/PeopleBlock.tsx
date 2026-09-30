import { cn } from '@/lib/utils'
import { useUpdateTask, type ProjectMember, type Task } from '../api'
import { Avatar, SectionLabel } from './ui'

interface Props {
  task: Task
  currentUserId: string
  members: ProjectMember[]
  isManager: boolean
}

/** Reporter, assignee (the reporter reassigns), reviewer (a manager designates — ADR-021). */
export function PeopleBlock({ task, currentUserId, members, isManager }: Props) {
  const updateTask = useUpdateTask(task.id, task.project_id)
  const userById = new Map(members.map(m => [m.user.id, m.user]))
  const reporter = userById.get(task.reporter_id)
  const assignee = task.assignee_id ? userById.get(task.assignee_id) : null
  const isAssignee = task.assignee_id === currentUserId
  const isReporter = task.reporter_id === currentUserId

  return (
    <div className="space-y-2">
      <SectionLabel>People</SectionLabel>
      <div className="space-y-3 text-sm">
        <div className="space-y-1.5">
          <p className="text-[11px] text-muted-foreground">Reporter</p>
          {reporter ? (
            <div className="flex items-center gap-2">
              <Avatar name={reporter.display_name} />
              <span>{reporter.display_name}</span>
            </div>
          ) : (
            <span className="text-muted-foreground text-xs">—</span>
          )}
        </div>
        <div className="space-y-1.5">
          <p className="text-[11px] text-muted-foreground">Assignee</p>
          {assignee ? (
            <div className={cn('flex items-center gap-2 rounded-md p-1', isAssignee && 'bg-primary/5')}>
              <Avatar name={assignee.display_name} />
              <span className="flex-1">{isAssignee ? 'You' : assignee.display_name}</span>
              {isReporter && (
                <button
                  className="text-xs text-muted-foreground hover:text-destructive"
                  onClick={() => updateTask.mutateAsync({ assignee_id: null, version: task.version })}
                >
                  ×
                </button>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-muted-foreground">
              <span className="text-xs">Unassigned</span>
              <button
                className="text-xs text-primary hover:underline"
                onClick={() => updateTask.mutateAsync({ assignee_id: currentUserId, version: task.version })}
              >
                Assign to me
              </button>
            </div>
          )}
          {isReporter && members.length > 0 && (
            <select
              className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-xs mt-1"
              value={task.assignee_id ?? ''}
              onChange={e => updateTask.mutateAsync({ assignee_id: e.target.value || null, version: task.version })}
            >
              <option value="">— Unassigned —</option>
              {members.map(m => (
                <option key={m.user.id} value={m.user.id}>{m.user.display_name}</option>
              ))}
            </select>
          )}
        </div>
        <div className="space-y-1.5">
          <p className="text-[11px] text-muted-foreground">Reviewer</p>
          {isManager ? (
            <select
              aria-label="Reviewer"
              className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-xs"
              value={task.reviewer_id ?? ''}
              onChange={e => updateTask.mutateAsync({ reviewer_id: e.target.value || null, version: task.version })}
            >
              <option value="">— Any reviewer —</option>
              {members.filter(m => m.is_reviewer && m.user.id !== task.assignee_id).map(m => (
                <option key={m.user.id} value={m.user.id}>{m.user.display_name}</option>
              ))}
            </select>
          ) : (
            <span className="text-xs text-muted-foreground">
              {task.reviewer_id ? userById.get(task.reviewer_id)?.display_name ?? task.reviewer_id.slice(0, 8) : 'Any reviewer'}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
