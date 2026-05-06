import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  useTask, useChildTasks, useProjectWorkflows, useProjectMembers,
  useTransitionStatus, useUpdateTask, useTaskComments,
  type Task, type Status,
} from './api'
import { CommentSection } from './CommentSection'

const PRIORITY_COLORS: Record<string, string> = {
  low:      'oklch(0.65 0.08 240)',
  medium:   'oklch(0.55 0.14 200)',
  high:     'oklch(0.60 0.18 55)',
  critical: 'oklch(0.55 0.22 25)',
}

interface Props {
  task: Task
  mode: 'page' | 'panel'
  currentUserId: string
}

export function TaskView({ task, mode, currentUserId }: Props) {
  const { data: workflows } = useProjectWorkflows(task.project_id)

  const { data: members } = useProjectMembers(task.project_id)
  const { data: parentTask } = useTask(task.parent_task_id)
  const { data: childTasks = [] } = useChildTasks(task.project_id, task.id)
  const { data: comments = [] } = useTaskComments(task.id)
  const transition = useTransitionStatus(task.project_id)
  const updateTask = useUpdateTask(task.id, task.project_id)

  // Use the task's own workflow, not the project default
  const taskWorkflow = workflows?.find(w => w.id === task.workflow_id)
    ?? workflows?.find(w => w.is_default)
    ?? workflows?.[0]
  const statuses: Status[] = [...(taskWorkflow?.statuses ?? [])].sort((a, b) => a.position - b.position)
  const transitions = taskWorkflow?.transitions ?? []
  const currentStatus = statuses.find(s => s.id === task.current_status_id)
  const userById = new Map(members?.items.map(m => [m.user.id, m.user]) ?? [])

  const [confirmingTransition, setConfirmingTransition] = useState<string | null>(null)

  const [transitionError, setTransitionError] = useState<string | null>(null)

  const inFinalStatus = currentStatus?.category === 'final'
  const typeKey = task.task_type?.key ?? 'task'
  const typeColor = task.task_type?.color ?? '#6366f1'
  const priorityColor = PRIORITY_COLORS[task.priority] ?? PRIORITY_COLORS.medium
  const assignee = task.assignee_id ? userById.get(task.assignee_id) : null
  const isAssignee = task.assignee_id === currentUserId
  const activeChildren = childTasks.filter(t => !t.deleted_at)

  function isBackward(toStatusId: string) {
    const target = statuses.find(s => s.id === toStatusId)
    return !!currentStatus && !!target && target.position < currentStatus.position
  }

  const nextStatuses = transitions
    .filter(t => t.from_status_id === task.current_status_id)
    .map(t => statuses.find(s => s.id === t.to_status_id))
    .filter((s): s is Status => !!s)

  async function performTransition(statusId: string) {
    setTransitionError(null); setConfirmingTransition(null)
    try {
      await transition.mutateAsync({ taskId: task.id, status_id: statusId })
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      if (code === 'TASK_BLOCKED_BY_SUBTASKS') {
        setTransitionError('Task is blocked: subtasks are not resolved yet.')
      } else {
        setTransitionError('Transition not allowed.')
      }
    }
  }

  // ── Reusable blocks ───────────────────────────────────────────────────────

  const titleBlock = (
    <div className={cn('space-y-1.5', mode === 'page' && 'space-y-2')}>
      <div className="flex items-center gap-2 flex-wrap">
        <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ background: priorityColor }} />
        <span className="rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase"
          style={{ background: typeColor + '22', color: typeColor }}>
          {typeKey}
        </span>
        {currentStatus && (
          <span className={cn('rounded px-2 py-0.5 text-xs font-medium bg-muted text-muted-foreground',
            mode === 'page' && 'rounded-md border px-2.5 py-1 text-sm')}>
            {currentStatus.name}
          </span>
        )}
      </div>
      <h1 className={cn('font-semibold leading-snug', mode === 'page' ? 'text-2xl' : 'text-base')}>
        {task.title}
      </h1>
    </div>
  )

  const transitionBlock = !inFinalStatus && nextStatuses.length > 0 && (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Move to</p>
      <div className="flex items-center gap-2 flex-wrap">
        {nextStatuses.map(s => (
          <Button key={s.id} size="sm"
            variant={isBackward(s.id) ? 'ghost' : 'outline'}
            className="h-7 text-xs"
            disabled={transition.isPending}
            onClick={() => isBackward(s.id) ? setConfirmingTransition(s.id) : performTransition(s.id)}>
            {isBackward(s.id) ? '← ' : ''}{s.name}
          </Button>
        ))}
      </div>
      {transitionError && <p className="text-xs text-destructive">{transitionError}</p>}
    </div>
  )

  const confirmBackwardBlock = confirmingTransition && (
    <div className="rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 p-3 space-y-2">
      <p className="text-sm font-medium">
        Move back to <strong>{statuses.find(s => s.id === confirmingTransition)?.name}</strong>?
      </p>
      <p className="text-xs text-muted-foreground">Backward transitions can lose progress.</p>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={() => setConfirmingTransition(null)}>Cancel</Button>
        <Button size="sm" onClick={() => performTransition(confirmingTransition)}>Confirm</Button>
      </div>
    </div>
  )



  const descriptionBlock = (
    <div className="space-y-1.5">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
      {task.description
        ? <p className="text-sm whitespace-pre-wrap leading-relaxed">{task.description}</p>
        : <p className="text-sm text-muted-foreground italic">No description.</p>}
    </div>
  )

  const childrenBlock = activeChildren.length > 0 && (
    <div className="space-y-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Child tasks ({activeChildren.length})
      </p>
      <ul className="space-y-0.5">
        {activeChildren.map(child => {
          const cs = statuses.find(s => s.id === child.current_status_id)
          const cls =
            cs?.category === 'final' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
            cs?.category === 'initial' ? 'bg-muted text-muted-foreground' :
            'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
          return (
            <li key={child.id}>
              <Link to={`/tasks/${child.key}`}
                className="flex items-center gap-2.5 rounded-md px-2.5 py-1.5 hover:bg-muted/50 transition-colors group">
                <span className="font-mono text-[11px] font-semibold text-muted-foreground/70 group-hover:text-primary transition-colors w-20 shrink-0">
                  {child.key}
                </span>
                <span className="flex-1 text-sm truncate">{child.title}</span>
                {cs && <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium shrink-0 ${cls}`}>{cs.name}</span>}
                {child.assignee_id && userById.get(child.assignee_id) && (
                  <span className="text-[11px] text-muted-foreground/60 shrink-0">
                    {userById.get(child.assignee_id)!.display_name}
                  </span>
                )}
              </Link>
            </li>
          )
        })}
      </ul>
    </div>
  )

  const assigneeBlock = (
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
  )

  const metaBlock = (
    <div className={cn('text-sm', mode === 'page' ? 'space-y-4' : 'grid grid-cols-2 gap-x-4 gap-y-2.5')}>
      <div>
        <p className="text-[11px] text-muted-foreground mb-0.5">Priority</p>
        <div className="flex items-center gap-1.5">
          {mode === 'page' && <div className="h-2 w-2 rounded-full" style={{ background: priorityColor }} />}
          <span className="capitalize font-medium">{task.priority}</span>
        </div>
      </div>
      <div>
        <p className="text-[11px] text-muted-foreground mb-0.5">Type</p>
        <span className="capitalize font-medium">{task.task_type?.name ?? typeKey}</span>
      </div>
      <div>
        <p className="text-[11px] text-muted-foreground mb-0.5">Reporter</p>
        <span className="font-medium">{userById.get(task.reporter_id)?.display_name ?? '…'}</span>
      </div>
      {task.due_date && (
        <div>
          <p className="text-[11px] text-muted-foreground mb-0.5">Due date</p>
          <span className="font-medium">{new Date(task.due_date).toLocaleDateString()}</span>
        </div>
      )}
      {parentTask && (
        <div className={mode === 'page' ? '' : 'col-span-2'}>
          <p className="text-[11px] text-muted-foreground mb-0.5">Parent</p>
          <Link to={`/tasks/${parentTask.key}`}
            className="flex items-center gap-1.5 text-xs hover:underline">
            <span className="font-mono font-semibold text-amber-600 dark:text-amber-400">{parentTask.key}</span>
            <span className="text-foreground truncate">{parentTask.title}</span>
          </Link>
        </div>
      )}
      <div>
        <p className="text-[11px] text-muted-foreground mb-0.5">Created</p>
        <span className="text-muted-foreground text-xs">
          {new Date(task.created_at).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' })}
        </span>
      </div>
    </div>
  )

  const commentsBlock = (
    <div className="border-t pt-4">
      <CommentSection taskId={task.id} currentUserId={currentUserId} userById={userById} />
    </div>
  )

  const debugBlock = (
    <details className="border-t pt-4">
      <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/50 hover:text-muted-foreground select-none">
        Debug
      </summary>
      <div className="mt-3 space-y-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/50 mb-1">Task</p>
          <pre className="rounded-md bg-muted p-3 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
            {JSON.stringify(task, null, 2)}
          </pre>
        </div>
        {comments.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/50 mb-1">
              Comments ({comments.length})
            </p>
            <pre className="rounded-md bg-muted p-3 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
              {JSON.stringify(comments, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </details>
  )

  // ── Layout ────────────────────────────────────────────────────────────────

  if (mode === 'page') {
    return (
      <div className="space-y-6">
        {titleBlock}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-5">
            {descriptionBlock}
            {transitionBlock}
            {confirmBackwardBlock}
            {childrenBlock && <div className="border-t pt-5">{childrenBlock}</div>}
            {commentsBlock}
            {debugBlock}
          </div>
          <div className="space-y-5">
            {assigneeBlock}
            {metaBlock}
          </div>
        </div>
      </div>
    )
  }

  // panel
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {titleBlock}
      {transitionBlock}
      {confirmBackwardBlock}
      {descriptionBlock}
      {childrenBlock}
      {assigneeBlock}
      {metaBlock}
      {commentsBlock}
      {debugBlock}
    </div>
  )
}
