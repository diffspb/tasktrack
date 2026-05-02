import { useParams, useNavigate, Link } from 'react-router-dom'
import type { AxiosError } from 'axios'
import { useState } from 'react'
import { ArrowLeft, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useAuth } from '@/features/auth/AuthProvider'
import {
  useTaskByKey, useTask, useProjectWorkflows, useProjectResolutions, useProjectMembers,
  useTransitionStatus, useUpdateTask,
  type Status, type Resolution,
} from './api'
import { CommentSection } from './CommentSection'

const PRIORITY_COLORS: Record<string, string> = {
  low:      'oklch(0.65 0.08 240)',
  medium:   'oklch(0.55 0.14 200)',
  high:     'oklch(0.60 0.18 55)',
  critical: 'oklch(0.55 0.22 25)',
}

export function TaskPage() {
  const { key } = useParams<{ key: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [copied, setCopied] = useState(false)

  const { data: task, isLoading, error } = useTaskByKey(key)
  const { data: parentTask } = useTask(task?.parent_task_id)
  const { data: workflows } = useProjectWorkflows(task?.project_id ?? '')
  const { data: resolutions = [] } = useProjectResolutions(task?.project_id ?? '')
  const { data: members } = useProjectMembers(task?.project_id)
  const transition = useTransitionStatus(task?.project_id ?? '')
  const updateTask = useUpdateTask(task?.id ?? '', task?.project_id ?? '')

  const defaultWorkflow = workflows?.find(w => w.is_default) ?? workflows?.[0]
  const statuses: Status[] = [...(defaultWorkflow?.statuses ?? [])].sort((a, b) => a.position - b.position)
  const transitions = defaultWorkflow?.transitions ?? []
  const currentStatus = statuses.find(s => s.id === task?.current_status_id)
  const userById = new Map(members?.items.map(m => [m.user.id, m.user]) ?? [])

  const [confirmingTransition, setConfirmingTransition] = useState<string | null>(null)
  const [pendingStatusId, setPendingStatusId] = useState<string | null>(null)
  const [selectedRes, setSelectedRes] = useState<string>('')
  const [transitionError, setTransitionError] = useState<string | null>(null)

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
        setSelectedRes(resolutions.find((r: Resolution) => r.is_default)?.id ?? '')
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

  function copyLink() {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto p-8 space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-muted-foreground">Task not found.</p>
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>Go back</Button>
      </div>
    )
  }

  const typeKey = task.task_type?.key ?? 'task'
  const priorityColor = PRIORITY_COLORS[task.priority] ?? PRIORITY_COLORS.medium
  const assignee = task.assignee_id ? userById.get(task.assignee_id) : null
  const isAssignee = task.assignee_id === user?.id
  const inFinalStatus = currentStatus?.category === 'final'

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto w-full px-6 py-6 space-y-6">
        {/* Breadcrumb / nav */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>
          <span className="text-muted-foreground/40">/</span>
          <Link
            to={`/projects/${task.project_id}/board`}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            Board
          </Link>
          <span className="text-muted-foreground/40">/</span>
          <span className="font-mono text-sm font-semibold text-muted-foreground">{task.key}</span>
          <div className="flex-1" />
          <button
            onClick={copyLink}
            className="flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copied' : 'Copy link'}
          </button>
        </div>

        {/* Header */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <div
              className="h-2.5 w-2.5 rounded-full shrink-0"
              style={{ background: priorityColor }}
              title={`Priority: ${task.priority}`}
            />
            <span
              className="rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase"
              style={{
                background: (task.task_type?.color ?? '#6366f1') + '22',
                color: task.task_type?.color ?? '#6366f1',
              }}
            >
              {typeKey}
            </span>
            {currentStatus && (
              <span className="rounded-md border px-2.5 py-1 text-sm font-medium">
                {currentStatus.name}
              </span>
            )}
          </div>
          <h1 className="text-2xl font-semibold leading-snug">{task.title}</h1>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-5">
            {/* Description */}
            <div className="space-y-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
              {task.description ? (
                <p className="text-sm text-foreground whitespace-pre-wrap leading-relaxed">{task.description}</p>
              ) : (
                <p className="text-sm text-muted-foreground italic">No description.</p>
              )}
            </div>

            {/* Comments */}
            <div className="border-t pt-5">
              <CommentSection
                taskId={task.id}
                currentUserId={user?.id ?? ''}
                userById={userById}
              />
            </div>

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
                  {resolutions.map((r: Resolution) => (
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
          </div>

          {/* Sidebar */}
          <div className="space-y-4 text-sm">
            {/* Assignee */}
            <div>
              <p className="text-[11px] text-muted-foreground mb-1">Assignee</p>
              {assignee ? (
                <div className={cn(
                  'flex items-center gap-2 rounded-md px-2.5 py-1.5',
                  isAssignee ? 'bg-primary/5 border border-primary/20' : 'bg-muted',
                )}>
                  <div className="h-6 w-6 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-bold shrink-0">
                    {assignee.display_name.slice(0, 2).toUpperCase()}
                  </div>
                  <span className="flex-1 text-sm">{isAssignee ? 'You' : assignee.display_name}</span>
                  {task.reporter_id === user?.id && (
                    <button
                      className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                      onClick={() => updateTask.mutateAsync({ assignee_id: null, version: task.version })}
                    >
                      remove
                    </button>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Unassigned</span>
                  <button
                    className="text-xs text-primary hover:underline"
                    onClick={() => updateTask.mutateAsync({ assignee_id: user?.id, version: task.version })}
                  >
                    Assign to me
                  </button>
                </div>
              )}
              {task.reporter_id === user?.id && members?.items && (
                <select
                  className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-xs mt-2"
                  value={task.assignee_id ?? ''}
                  onChange={e => updateTask.mutateAsync({ assignee_id: e.target.value || null, version: task.version })}
                >
                  <option value="">— Unassigned —</option>
                  {members.items.map(m => (
                    <option key={m.user.id} value={m.user.id}>{m.user.display_name}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Priority */}
            <div>
              <p className="text-[11px] text-muted-foreground mb-0.5">Priority</p>
              <div className="flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full" style={{ background: priorityColor }} />
                <span className="capitalize font-medium">{task.priority}</span>
              </div>
            </div>

            {/* Parent (epic) */}
            {parentTask && (
              <div>
                <p className="text-[11px] text-muted-foreground mb-0.5">Parent</p>
                <Link
                  to={`/tasks/${parentTask.key}`}
                  className="flex items-center gap-1.5 text-xs hover:underline"
                >
                  <span className="font-mono font-semibold text-amber-600 dark:text-amber-400">{parentTask.key}</span>
                  <span className="text-foreground truncate">{parentTask.title}</span>
                </Link>
              </div>
            )}

            {/* Reporter */}
            <div>
              <p className="text-[11px] text-muted-foreground mb-0.5">Reporter</p>
              <span className="font-medium">
                {userById.get(task.reporter_id)?.display_name ?? '…'}
              </span>
            </div>

            {/* Due date */}
            {task.due_date && (
              <div>
                <p className="text-[11px] text-muted-foreground mb-0.5">Due date</p>
                <span className="font-medium">{new Date(task.due_date).toLocaleDateString()}</span>
              </div>
            )}

            {/* Created */}
            <div>
              <p className="text-[11px] text-muted-foreground mb-0.5">Created</p>
              <span className="text-muted-foreground text-xs">
                {new Date(task.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' })}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
