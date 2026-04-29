import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { Task, Status, Resolution } from './api'
import { useTransitionStatus } from './api'

const GS_STYLES: Record<string, { cls: string; label: string }> = {
  open:              { cls: 'bg-muted text-muted-foreground',                                 label: 'Open' },
  in_progress:       { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',   label: 'In Progress' },
  awaiting_decision: { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300', label: 'Awaiting Decision' },
  in_revision:       { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', label: 'In Revision' },
  decided:           { cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',  label: 'Decided' },
  closed:            { cls: 'bg-muted text-muted-foreground',                                 label: 'Closed' },
}

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
  const [pendingStatusId, setPendingStatusId] = useState<string | null>(null)
  const [selectedRes, setSelectedRes] = useState<string>('')
  const [transitionError, setTransitionError] = useState<string | null>(null)
  const transition = useTransitionStatus(projectId)

  const myAssignment = task?.assignments.find(a => a.user_id === currentUserId)
  const currentStatus = statuses.find(s => s.id === myAssignment?.current_status_id)
  const nextStatuses = transitions
    .filter(t => t.from_status_id === myAssignment?.current_status_id)
    .map(t => statuses.find(s => s.id === t.to_status_id))
    .filter((s): s is Status => !!s)

  const statusMap = Object.fromEntries(statuses.map(s => [s.id, s.name]))
  const gs = task ? (GS_STYLES[task.global_status] ?? GS_STYLES.open) : null

  async function handleTransition(statusId: string, resolutionId?: string) {
    if (!myAssignment) return
    setTransitionError(null)
    try {
      await transition.mutateAsync({ assignmentId: myAssignment.id, status_id: statusId, resolution_id: resolutionId })
      setPendingStatusId(null)
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      if (code === 'RESOLUTION_REQUIRED') {
        setPendingStatusId(statusId)
        setSelectedRes(resolutions.find(r => r.is_default)?.id ?? '')
      } else {
        setTransitionError('Transition not allowed.')
      }
    }
  }

  return (
    <Sheet open={!!task} onOpenChange={v => { if (!v) { setPendingStatusId(null); setTransitionError(null); onClose() } }}>
      <SheetContent className="w-[460px] sm:max-w-[460px] overflow-y-auto">
        {task && (
          <div className="flex flex-col gap-5 p-6 pt-2">
            <SheetHeader>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs font-semibold text-muted-foreground">{task.key}</span>
                {gs && <span className={cn('rounded px-2 py-0.5 text-xs font-medium', gs.cls)}>{gs.label}</span>}
              </div>
              <SheetTitle className="text-left text-base leading-snug">{task.title}</SheetTitle>
            </SheetHeader>

            {/* My status & transitions */}
            {myAssignment && (
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">My Status</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="rounded-md border px-2.5 py-1 text-sm font-medium">
                    {currentStatus?.name ?? '—'}
                  </span>
                  {nextStatuses.length > 0 && (
                    <>
                      <span className="text-muted-foreground/40 text-xs">→</span>
                      {nextStatuses.map(s => (
                        <Button key={s.id} size="sm" variant="outline" className="h-7 text-xs"
                          disabled={transition.isPending}
                          onClick={() => handleTransition(s.id)}>
                          {s.name}
                        </Button>
                      ))}
                    </>
                  )}
                </div>
                {transitionError && <p className="text-xs text-destructive">{transitionError}</p>}
              </div>
            )}

            {/* Resolution picker (shown when final status requires it) */}
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
                    onClick={() => handleTransition(pendingStatusId, selectedRes)}>
                    Confirm
                  </Button>
                </div>
              </div>
            )}

            {/* Metadata */}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-[11px] text-muted-foreground mb-0.5">Priority</p>
                <p className="capitalize font-medium">{task.priority}</p>
              </div>
              {task.due_date && (
                <div>
                  <p className="text-[11px] text-muted-foreground mb-0.5">Due date</p>
                  <p className="font-medium">{new Date(task.due_date).toLocaleDateString()}</p>
                </div>
              )}
              <div>
                <p className="text-[11px] text-muted-foreground mb-0.5">Type</p>
                <p className="capitalize font-medium">{task.task_type}</p>
              </div>
            </div>

            {/* Description */}
            {task.description && (
              <div className="space-y-1.5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{task.description}</p>
              </div>
            )}

            {/* Assignees */}
            {task.assignments.length > 0 && (
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Assignees</p>
                <div className="space-y-1.5">
                  {task.assignments.map(a => (
                    <div key={a.id} className={cn(
                      'flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm',
                      a.user_id === currentUserId ? 'bg-primary/5 border border-primary/20' : 'bg-muted',
                    )}>
                      <div className="h-6 w-6 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-bold shrink-0">
                        {a.user_id.slice(-2).toUpperCase()}
                      </div>
                      <span className="flex-1 text-sm">
                        {a.user_id === currentUserId ? 'You' : `…${a.user_id.slice(-8)}`}
                      </span>
                      <Badge variant="outline" className="text-[10px] h-5 capitalize">{a.role}</Badge>
                      <span className="text-xs text-muted-foreground">{statusMap[a.current_status_id] ?? '—'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
