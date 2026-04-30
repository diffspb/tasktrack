import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { Task, Status, Resolution, GlobalStatus } from './api'
import { useTransitionStatus, useAssignUser, useProjectMembers } from './api'
import { SolutionEditor } from '@/features/decision-process/SolutionEditor'
import { SolutionList } from '@/features/decision-process/SolutionList'
import { DecisionPanel } from '@/features/decision-process/DecisionPanel'
import { DecisionView } from '@/features/decision-process/DecisionView'
import { DecisionCriteriaPanel } from '@/features/decision-process/DecisionCriteriaPanel'
import { AssigneePicker } from '@/features/decision-process/AssigneePicker'

const GS_STYLES: Record<GlobalStatus, { cls: string; label: string }> = {
  open:              { cls: 'bg-muted text-muted-foreground',                                          label: 'Open' },
  in_progress:       { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',        label: 'In Progress' },
  awaiting_decision: { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300', label: 'Awaiting Decision' },
  in_revision:       { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', label: 'In Revision' },
  decided:           { cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',    label: 'Decided' },
  closed:            { cls: 'bg-muted text-muted-foreground',                                          label: 'Closed' },
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
  const [confirmingTransition, setConfirmingTransition] = useState<string | null>(null)
  const [selectedRes, setSelectedRes] = useState<string>('')
  const [transitionError, setTransitionError] = useState<string | null>(null)
  const transition = useTransitionStatus(projectId)
  const assignUser = useAssignUser(projectId)
  const { data: members } = useProjectMembers(projectId)

  const myAssignment = task?.assignments.find(a => a.user_id === currentUserId)
  const currentStatus = statuses.find(s => s.id === myAssignment?.current_status_id)
  const inFinalStatus = currentStatus?.category === 'final'

  // Backward transitions need confirmation (lower position than current).
  function isBackward(toStatusId: string): boolean {
    if (!currentStatus) return false
    const target = statuses.find(s => s.id === toStatusId)
    if (!target) return false
    return target.position < currentStatus.position
  }

  const nextStatuses = transitions
    .filter(t => t.from_status_id === myAssignment?.current_status_id)
    .map(t => statuses.find(s => s.id === t.to_status_id))
    .filter((s): s is Status => !!s)

  const statusMap = Object.fromEntries(statuses.map(s => [s.id, s.name]))
  const userById = new Map(members?.items.map(m => [m.user.id, m.user]) ?? [])
  const gs = task ? (GS_STYLES[task.global_status] ?? GS_STYLES.open) : null

  const isReporter = task?.reporter_id === currentUserId
  const isDecisionMaker = task?.decision_maker_id === currentUserId
  const myRole = myAssignment?.role
  const canSeeOthersSolutions = myRole !== 'consultant' || task?.global_status === 'decided' || task?.global_status === 'closed'
  const taskClosed = task?.global_status === 'closed' || task?.global_status === 'decided'
  const leadCount = task?.assignments.filter(a => a.role === 'lead').length ?? 0
  const isMultiLead = leadCount > 1

  async function performTransition(statusId: string, resolutionId?: string) {
    if (!myAssignment) return
    setTransitionError(null)
    setConfirmingTransition(null)
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

  function handleTransitionClick(statusId: string) {
    // Final status auto-prompts resolution; backward needs explicit confirm.
    if (isBackward(statusId)) {
      setConfirmingTransition(statusId)
    } else {
      performTransition(statusId)
    }
  }

  async function handleAssignMe() {
    if (!task) return
    await assignUser.mutateAsync({ taskId: task.id, userId: currentUserId, role: 'lead' })
  }

  return (
    <Sheet open={!!task} onOpenChange={v => {
      if (!v) {
        setPendingStatusId(null); setConfirmingTransition(null); setTransitionError(null); onClose()
      }
    }}>
      <SheetContent className="w-[480px] sm:max-w-[480px] overflow-y-auto">
        {task && (
          <div className="flex flex-col gap-5 p-6 pt-2">
            <SheetHeader>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-xs font-semibold text-muted-foreground">{task.key}</span>
                {gs && <span className={cn('rounded px-2 py-0.5 text-xs font-medium', gs.cls)}>{gs.label}</span>}
                {task.allow_multi_accept && (
                  <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                    multi-accept
                  </span>
                )}
              </div>
              <SheetTitle className="text-left text-base leading-snug">{task.title}</SheetTitle>
            </SheetHeader>

            {/* Assign-to-me — only when no assignment and task is open */}
            {!myAssignment && !taskClosed && (
              <Button variant="outline" size="sm" className="w-fit"
                disabled={assignUser.isPending} onClick={handleAssignMe}>
                {assignUser.isPending ? 'Assigning…' : 'Assign to me'}
              </Button>
            )}

            {/* My status & transitions (lead/reviewer/consultant) */}
            {myAssignment && !taskClosed && (
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">My Status</p>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="rounded-md border px-2.5 py-1 text-sm font-medium">
                    {currentStatus?.name ?? '—'}
                  </span>
                  <Badge variant="outline" className="text-[10px] capitalize h-5">{myRole}</Badge>
                  {nextStatuses.length > 0 && (
                    <>
                      <span className="text-muted-foreground/40 text-xs">→</span>
                      {nextStatuses.map(s => (
                        <Button key={s.id} size="sm"
                          variant={isBackward(s.id) ? 'ghost' : 'outline'}
                          className="h-7 text-xs"
                          disabled={transition.isPending}
                          onClick={() => handleTransitionClick(s.id)}>
                          {isBackward(s.id) ? '← ' : ''}{s.name}
                        </Button>
                      ))}
                    </>
                  )}
                </div>
                {transitionError && <p className="text-xs text-destructive">{transitionError}</p>}
              </div>
            )}

            {/* Backward-transition confirmation */}
            {confirmingTransition && (
              <div className="rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 p-3 space-y-2">
                <p className="text-sm font-medium">
                  Move back to <strong>{statusMap[confirmingTransition]}</strong>?
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

            {/* Resolution picker (forced when going to final) */}
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

            {/* My Solution editor — leads only, in DP context (multi-lead OR DM is set) */}
            {myAssignment?.role === 'lead' && (isMultiLead || task.decision_maker_id) && (
              <SolutionEditor
                projectId={projectId}
                taskId={task.id}
                assignmentId={myAssignment.id}
                inFinalStatus={!!inFinalStatus}
                taskClosed={taskClosed}
              />
            )}

            {/* Decision panel — DM during awaiting/in_revision */}
            {isDecisionMaker && <DecisionPanel projectId={projectId} task={task} />}

            {/* Decision view — when decision exists */}
            {(task.global_status === 'decided' || task.global_status === 'closed') && (
              <DecisionView projectId={projectId} task={task} isDecisionMaker={isDecisionMaker} />
            )}

            {/* All solutions — visible to lead/reviewer/DM (consultant after Decision) */}
            {canSeeOthersSolutions && (isMultiLead || task.global_status === 'decided' || task.global_status === 'closed') && (
              <div className="space-y-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">All Solutions</p>
                <SolutionList
                  projectId={projectId}
                  taskId={task.id}
                  assignments={task.assignments}
                  currentUserId={currentUserId}
                />
              </div>
            )}

            {/* Decision criteria — author/manager can edit before lock */}
            {(task.decision_maker_id || isMultiLead) && (
              <DecisionCriteriaPanel
                projectId={projectId}
                taskId={task.id}
                canEdit={isReporter || isDecisionMaker}
              />
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
              {task.decision_maker_id && (
                <div>
                  <p className="text-[11px] text-muted-foreground mb-0.5">Decision-maker</p>
                  <p className="font-medium">
                    {userById.get(task.decision_maker_id)?.display_name ?? '…'}
                    {isDecisionMaker && <span className="text-muted-foreground"> (you)</span>}
                  </p>
                </div>
              )}
            </div>

            {/* Description */}
            {task.description && (
              <div className="space-y-1.5">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
                <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">{task.description}</p>
              </div>
            )}

            {/* Assignees + add */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Assignees ({task.assignments.length})
                </p>
              </div>
              <div className="space-y-1.5">
                {task.assignments.map(a => {
                  const u = userById.get(a.user_id)
                  return (
                    <div key={a.id} className={cn(
                      'flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm',
                      a.user_id === currentUserId ? 'bg-primary/5 border border-primary/20' : 'bg-muted',
                    )}>
                      <div className="h-6 w-6 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-bold shrink-0">
                        {(u?.display_name ?? '??').slice(0, 2).toUpperCase()}
                      </div>
                      <span className="flex-1 text-sm">
                        {a.user_id === currentUserId ? 'You' : u?.display_name ?? '…'}
                      </span>
                      <Badge variant="outline" className="text-[10px] h-5 capitalize">{a.role}</Badge>
                      <span className="text-xs text-muted-foreground">{statusMap[a.current_status_id] ?? '—'}</span>
                    </div>
                  )
                })}
              </div>
              <AssigneePicker
                projectId={projectId}
                taskId={task.id}
                assignments={task.assignments}
                canEdit={isReporter && !taskClosed}
              />
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
