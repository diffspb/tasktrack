import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
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
    if (isBackward(statusId)) {
      setConfirmingTransition(statusId)
    } else {
      performTransition(statusId)
    }
  }

  async function handleAssigneeChange(userId: string | null) {
    if (!task) return
    await updateTask.mutateAsync({ assignee_id: userId, version: task.version })
  }

  function handleClose() {
    setPendingStatusId(null)
    setConfirmingTransition(null)
    setTransitionError(null)
    onClose()
  }

  const inFinalStatus = currentStatus?.category === 'final'
  const assignee = task?.assignee_id ? userById.get(task.assignee_id) : null
  const isAssignee = task?.assignee_id === currentUserId
  const typeKey = task?.task_type?.key ?? 'task'

  return (
    <Sheet open={!!task} onOpenChange={v => { if (!v) handleClose() }}>
      <SheetContent className="w-[480px] sm:max-w-[480px] overflow-y-auto">
        {task && (
          <div className="flex flex-col gap-5 p-6 pt-2">
            <SheetHeader>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs font-semibold text-muted-foreground">{task.key}</span>
                <span className="text-xs text-muted-foreground capitalize bg-muted rounded px-1.5 py-0.5">
                  {typeKey}
                </span>
                {currentStatus && (
                  <span className="rounded px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground">
                    {currentStatus.name}
                  </span>
                )}
              </div>
              <SheetTitle className="text-left text-base leading-snug">{task.title}</SheetTitle>
            </SheetHeader>

            {/* Status transitions */}
            {!inFinalStatus && nextStatuses.length > 0 && (
              <div className="space-y-2">
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

            {/* Backward-transition confirmation */}
            {confirmingTransition && (
              <div className="rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 p-3 space-y-2">
                <p className="text-sm font-medium">
                  Move back to <strong>{statuses.find(s => s.id === confirmingTransition)?.name}</strong>?
                </p>
                <p className="text-xs text-muted-foreground">
                  Backward transitions can lose progress. Confirm to proceed.
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
                <p className="text-sm font-medium">Choose a resolution to close this task</p>
                <div className="flex flex-wrap gap-1.5">
                  {resolutions.map(r => (
                    <button key={r.id} type="button" onClick={() => setSelectedRes(r.id)}
                      className={cn(
                        'rounded-md border px-2.5 py-1 text-xs transition-colors',
                        selectedRes === r.id
                          ? 'border-primary bg-primary/10 text-primary font-medium'
                          : 'border-border text-muted-foreground',
                      )}>
                      {r.name}
                    </button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setPendingStatusId(null)}>Cancel</Button>
                  <Button size="sm" disabled={!selectedRes || transition.isPending}
                    onClick={() => performTransition(pendingStatusId, selectedRes)}>
                    Confirm
                  </Button>
                </div>
              </div>
            )}

            {/* Description */}
            {task.description && (
              <div className="space-y-1.5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{task.description}</p>
              </div>
            )}

            {/* Assignee */}
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Assignee</p>
              {assignee ? (
                <div className={cn(
                  'flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm',
                  isAssignee ? 'bg-primary/5 border border-primary/20' : 'bg-muted',
                )}>
                  <div className="h-6 w-6 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-bold shrink-0">
                    {assignee.display_name.slice(0, 2).toUpperCase()}
                  </div>
                  <span className="flex-1 text-sm">
                    {isAssignee ? 'You' : assignee.display_name}
                  </span>
                  {task.reporter_id === currentUserId && (
                    <button
                      className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                      onClick={() => handleAssigneeChange(null)}
                    >
                      remove
                    </button>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Unassigned</span>
                  <button
                    className="text-xs text-primary hover:underline"
                    onClick={() => handleAssigneeChange(currentUserId)}
                  >
                    Assign to me
                  </button>
                </div>
              )}
              {/* Assignee picker for reporter */}
              {task.reporter_id === currentUserId && members?.items && (
                <select
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs mt-1"
                  value={task.assignee_id ?? ''}
                  onChange={e => handleAssigneeChange(e.target.value || null)}
                >
                  <option value="">— Unassigned —</option>
                  {members.items.map(m => (
                    <option key={m.user.id} value={m.user.id}>{m.user.display_name}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Metadata */}
            <div className="grid grid-cols-2 gap-3 text-sm">
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
                  <p className="text-[11px] text-muted-foreground mb-0.5">Parent task</p>
                  <p className="font-medium text-primary text-xs">{task.parent_task_id}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
