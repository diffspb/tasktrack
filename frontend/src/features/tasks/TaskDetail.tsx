import { useState } from 'react'
import type { AxiosError } from 'axios'
import { X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { Task, Status, Resolution } from './api'
import { useTransitionStatus, useUpdateTask, useProjectMembers } from './api'

interface Props {
  task: Task | null
  statuses: Status[]
  transitions: { from_status_id: string; to_status_id: string }[]
  resolutions: Resolution[]
  projectId: string
  currentUserId: string
  onClose: () => void
}

export function TaskDetail({ task, statuses, transitions, resolutions, projectId, currentUserId, onClose }: Props) {
  const [confirmingTransition, setConfirmingTransition] = useState<string | null>(null)
  const [pendingStatusId, setPendingStatusId] = useState<string | null>(null)
  const [selectedRes, setSelectedRes] = useState<string>('')
  const [transitionError, setTransitionError] = useState<string | null>(null)
  const transition = useTransitionStatus(projectId)
  const updateTask = useUpdateTask(task?.id ?? '', projectId)
  const { data: members } = useProjectMembers(projectId)

  const currentStatus = statuses.find(s => s.id === task?.current_status_id)
  const userById = new Map(members?.items.map(m => [m.user.id, m.user]) ?? [])

  function isBackward(toStatusId: string): boolean {
    if (!currentStatus) return false
    const target = statuses.find(s => s.id === toStatusId)
    return !!target && target.position < currentStatus.position
  }

  const nextStatuses = transitions
    .filter(t => t.from_status_id === task?.current_status_id)
    .map(t => statuses.find(s => s.id === t.to_status_id))
    .filter((s): s is Status => !!s)

  async function performTransition(statusId: string, resolutionId?: string) {
    if (!task) return
    setTransitionError(null)
    setConfirmingTransition(null)
    try {
      await transition.mutateAsync({ taskId: task.id, status_id: statusId, resolution_id: resolutionId })
      setPendingStatusId(null)
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      if (code === 'RESOLUTION_REQUIRED') {
        setPendingStatusId(statusId)
        setSelectedRes(resolutions.find(r => r.is_default)?.id ?? '')
      } else if (code === 'TASK_BLOCKED_BY_SUBTASKS') {
        setTransitionError('Task is blocked: subtasks are not resolved yet.')
      } else {
        setTransitionError('Transition not allowed.')
      }
    }
  }

  function handleTransitionClick(statusId: string) {
    if (isBackward(statusId)) setConfirmingTransition(statusId)
    else performTransition(statusId)
  }

  function handleClose() {
    setPendingStatusId(null); setConfirmingTransition(null); setTransitionError(null)
    onClose()
  }

  const inFinalStatus = currentStatus?.category === 'final'
  const assignee = task?.assignee_id ? userById.get(task.assignee_id) : null
  const isAssignee = task?.assignee_id === currentUserId
  const typeKey = task?.task_type?.key ?? 'task'

  if (!task) return null

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
        {currentStatus && (
          <span className="rounded px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground">
            {currentStatus.name}
          </span>
        )}
        <div className="flex-1" />
        <button
          onClick={handleClose}
          className="rounded p-1 text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <h2 className="text-base font-semibold leading-snug">{task.title}</h2>

        {/* Status transitions */}
        {!inFinalStatus && nextStatuses.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Move to</p>
            <div className="flex items-center gap-2 flex-wrap">
              {nextStatuses.map(s => (
                <Button key={s.id} size="sm"
                  variant={isBackward(s.id) ? 'ghost' : 'outline'}
                  className="h-7 text-xs"
                  disabled={transition.isPending}
                  onClick={() => handleTransitionClick(s.id)}>
                  {isBackward(s.id) ? '← ' : ''}{s.name}
                </Button>
              ))}
            </div>
            {transitionError && <p className="text-xs text-destructive">{transitionError}</p>}
          </div>
        )}

        {/* Backward confirmation */}
        {confirmingTransition && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 p-3 space-y-2">
            <p className="text-sm font-medium">
              Move back to <strong>{statuses.find(s => s.id === confirmingTransition)?.name}</strong>?
            </p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setConfirmingTransition(null)}>Cancel</Button>
              <Button size="sm" onClick={() => performTransition(confirmingTransition)}>Confirm</Button>
            </div>
          </div>
        )}

        {/* Resolution picker */}
        {pendingStatusId && (
          <div className="rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 p-3 space-y-2.5">
            <p className="text-sm font-medium">Choose a resolution</p>
            <div className="flex flex-wrap gap-1.5">
              {resolutions.map(r => (
                <button key={r.id} type="button" onClick={() => setSelectedRes(r.id)}
                  className={cn('rounded-md border px-2.5 py-1 text-xs transition-colors',
                    selectedRes === r.id ? 'border-primary bg-primary/10 text-primary font-medium' : 'border-border text-muted-foreground')}>
                  {r.name}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setPendingStatusId(null)}>Cancel</Button>
              <Button size="sm" disabled={!selectedRes || transition.isPending}
                onClick={() => performTransition(pendingStatusId, selectedRes)}>Confirm</Button>
            </div>
          </div>
        )}

        {/* Description */}
        {task.description && (
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
            <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{task.description}</p>
          </div>
        )}

        {/* Assignee */}
        <div className="space-y-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Assignee</p>
          {assignee ? (
            <div className={cn('flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm',
              isAssignee ? 'bg-primary/5 border border-primary/20' : 'bg-muted')}>
              <div className="h-6 w-6 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-bold shrink-0">
                {assignee.display_name.slice(0, 2).toUpperCase()}
              </div>
              <span className="flex-1">{isAssignee ? 'You' : assignee.display_name}</span>
              {task.reporter_id === currentUserId && (
                <button className="text-xs text-muted-foreground hover:text-destructive"
                  onClick={() => updateTask.mutateAsync({ assignee_id: null, version: task.version })}>
                  remove
                </button>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              Unassigned
              <button className="text-xs text-primary hover:underline"
                onClick={() => updateTask.mutateAsync({ assignee_id: currentUserId, version: task.version })}>
                Assign to me
              </button>
            </div>
          )}
          {task.reporter_id === currentUserId && members?.items && (
            <select
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs"
              value={task.assignee_id ?? ''}
              onChange={e => updateTask.mutateAsync({ assignee_id: e.target.value || null, version: task.version })}>
              <option value="">— Unassigned —</option>
              {members.items.map(m => (
                <option key={m.user.id} value={m.user.id}>{m.user.display_name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Metadata grid */}
        <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-sm pt-1">
          <div>
            <p className="text-[11px] text-muted-foreground mb-0.5">Priority</p>
            <p className="capitalize font-medium">{task.priority}</p>
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground mb-0.5">Type</p>
            <p className="capitalize font-medium">{task.task_type?.name ?? typeKey}</p>
          </div>
          {task.due_date && (
            <div>
              <p className="text-[11px] text-muted-foreground mb-0.5">Due date</p>
              <p className="font-medium">{new Date(task.due_date).toLocaleDateString()}</p>
            </div>
          )}
          {task.parent_task_id && (
            <div>
              <p className="text-[11px] text-muted-foreground mb-0.5">Parent</p>
              <p className="font-medium text-xs text-primary">{task.parent_task_id.slice(0, 8)}…</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
