import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { AxiosError } from 'axios'
import { ArrowDown, ArrowRight, ArrowUp, ChevronsUp, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  useTask, useChildTasks, useProjectWorkflows, useProjectMembers,
  useTransitionStatus, useUpdateTask, useTaskComments, useTaskLinks, useLinkTypes, useDeleteTaskLink,
  type Task, type Status,
} from './api'
import { CommentSection } from './CommentSection'
import { CreateTaskModal } from './CreateTaskModal'
import { LinkTaskDialog } from './LinkTaskDialog'
import { TaskTypeIcon, TYPE_COLORS } from './TaskTypeIcon'

const PRIORITY_CONFIG: Record<string, {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Icon: React.ComponentType<any>
  color: string
}> = {
  low:      { Icon: ArrowDown,  color: 'oklch(0.65 0.08 240)' },
  medium:   { Icon: ArrowRight, color: 'oklch(0.55 0.14 200)' },
  high:     { Icon: ArrowUp,    color: 'oklch(0.60 0.18 55)'  },
  critical: { Icon: ChevronsUp, color: 'oklch(0.55 0.22 25)'  },
}

const STATUS_DOT: Record<string, string> = {
  initial:      'oklch(0.6 0 0)',
  intermediate: 'oklch(0.55 0.14 230)',
  final:        'oklch(0.55 0.15 150)',
}

function Avatar({ name }: { name: string }) {
  return (
    <div className="h-7 w-7 rounded-full bg-muted-foreground/15 flex items-center justify-center text-[11px] font-bold shrink-0 select-none">
      {name.slice(0, 2).toUpperCase()}
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60 mb-2">
      {children}
    </p>
  )
}

interface Props {
  task: Task
  mode: 'page' | 'panel'
  currentUserId: string
}

export function TaskView({ task, mode, currentUserId }: Props) {
  const { data: workflows }           = useProjectWorkflows(task.project_id)
  const { data: members }             = useProjectMembers(task.project_id)
  const { data: parentTask }          = useTask(task.parent_task_id)
  const { data: childTasks = [] }     = useChildTasks(task.project_id, task.id)
  const { data: comments = [] }       = useTaskComments(task.id)
  const { data: taskLinks = [] }      = useTaskLinks(task.id)
  const { data: linkTypes = [] }      = useLinkTypes()
  const deleteLink                    = useDeleteTaskLink(task.id)
  const transition                    = useTransitionStatus(task.project_id)
  const updateTask                    = useUpdateTask(task.id, task.project_id)

  const taskWorkflow = workflows?.find(w => w.id === task.workflow_id)
    ?? workflows?.find(w => w.is_default)
    ?? workflows?.[0]
  const statuses: Status[] = [...(taskWorkflow?.statuses ?? [])].sort((a, b) => a.position - b.position)
  const transitions         = taskWorkflow?.transitions ?? []
  const currentStatus       = statuses.find(s => s.id === task.current_status_id)
  const userById            = new Map(members?.items.map(m => [m.user.id, m.user]) ?? [])

  const [confirmingTransition, setConfirmingTransition] = useState<string | null>(null)
  const [transitionError,      setTransitionError]      = useState<string | null>(null)
  const [activeTab,            setActiveTab]            = useState<'comments' | 'history'>('comments')

  const [createChildOpen,  setCreateChildOpen]  = useState(false)
  const [editingPriority,  setEditingPriority]  = useState(false)
  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft,   setTitleDraft]   = useState('')
  const [editingDesc,  setEditingDesc]  = useState(false)
  const [descDraft,    setDescDraft]    = useState('')
  const [editingStartDate, setEditingStartDate] = useState(false)
  const [editingDueDate,   setEditingDueDate]   = useState(false)
  const [linkDialogOpen,   setLinkDialogOpen]   = useState(false)

  async function saveTitle() {
    const trimmed = titleDraft.trim()
    setEditingTitle(false)
    if (trimmed && trimmed !== task.title) {
      await updateTask.mutateAsync({ title: trimmed, version: task.version })
    }
  }

  async function saveDesc() {
    const val = descDraft.trim() || null
    setEditingDesc(false)
    if (val !== (task.description ?? null)) {
      await updateTask.mutateAsync({ description: val ?? undefined, version: task.version })
    }
  }

  const inFinalStatus  = currentStatus?.category === 'final'
  const typeKey        = task.task_type?.key ?? 'task'
  const typeColor      = task.task_type?.color ?? TYPE_COLORS[typeKey] ?? TYPE_COLORS.task
  const assignee       = task.assignee_id ? userById.get(task.assignee_id) : null
  const reporter       = userById.get(task.reporter_id)
  const isAssignee     = task.assignee_id === currentUserId
  const activeChildren = childTasks.filter(t => !t.deleted_at)

  const priorityCfg  = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium
  const PriorityIcon = priorityCfg.Icon
  const priorityColor = priorityCfg.color

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
      setTransitionError(
        code === 'TASK_BLOCKED_BY_SUBTASKS'
          ? 'Task is blocked: subtasks are not resolved yet.'
          : 'Transition not allowed.',
      )
    }
  }

  // ── Blocks ──────────────────────────────────────────────────────────────────

  const titleBlock = editingTitle ? (
    <div className="space-y-2">
      <input
        autoFocus
        value={titleDraft}
        onChange={e => setTitleDraft(e.target.value)}
        onKeyDown={e => {
          if (e.key === 'Enter') saveTitle()
          if (e.key === 'Escape') setEditingTitle(false)
        }}
        onBlur={saveTitle}
        className={cn(
          'w-full font-semibold bg-transparent border-b-2 border-primary outline-none leading-snug',
          mode === 'page' ? 'text-2xl' : 'text-base',
        )}
      />
      <div className="flex gap-2">
        <Button size="sm" onMouseDown={e => e.preventDefault()} onClick={saveTitle}>Save</Button>
        <Button size="sm" variant="ghost"
          onMouseDown={e => e.preventDefault()}
          onClick={() => setEditingTitle(false)}
        >Cancel</Button>
      </div>
    </div>
  ) : (
    <h1
      onClick={() => { setTitleDraft(task.title); setEditingTitle(true) }}
      className={cn(
        'font-semibold leading-snug cursor-text rounded px-1 -mx-1',
        'hover:bg-muted/40 transition-colors',
        mode === 'page' ? 'text-2xl' : 'text-base',
      )}
    >
      {task.title}
    </h1>
  )

  const actionsBlock = !inFinalStatus && nextStatuses.length > 0 && (
    <div className="space-y-1.5">
      <SectionLabel>Move to</SectionLabel>
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

  const detailsBlock = (
    <div className="space-y-2">
      <SectionLabel>Details</SectionLabel>
      <div className="space-y-0.5 text-sm">
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Type</span>
          <TaskTypeIcon typeKey={typeKey} color={typeColor} size={13} />
          <span className="capitalize">{task.task_type?.name ?? typeKey}</span>
        </div>
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Priority</span>
          {editingPriority ? (
            <select
              autoFocus
              defaultValue={task.priority}
              onChange={async e => {
                const val = e.target.value as typeof task.priority
                setEditingPriority(false)
                if (val !== task.priority)
                  await updateTask.mutateAsync({ priority: val, version: task.version })
              }}
              onBlur={() => setEditingPriority(false)}
              className="text-sm bg-background border border-input rounded px-1.5 py-0.5 outline-none focus:border-primary capitalize"
            >
              {(['low', 'medium', 'high', 'critical'] as const).map(p => (
                <option key={p} value={p} className="capitalize">{p}</option>
              ))}
            </select>
          ) : (
            <button
              onClick={() => setEditingPriority(true)}
              className="flex items-center gap-1.5 rounded px-1 -mx-1 hover:bg-muted/40 transition-colors"
            >
              <PriorityIcon size={13} style={{ color: priorityColor, flexShrink: 0 }} />
              <span className="text-sm capitalize">{task.priority}</span>
            </button>
          )}
        </div>
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Status</span>
          <div
            className="h-2 w-2 rounded-full shrink-0"
            style={{ background: STATUS_DOT[currentStatus?.category ?? 'initial'] }}
          />
          <span>{currentStatus?.name ?? '—'}</span>
        </div>
        {parentTask && (
          <div className="flex items-center gap-2 py-1.5">
            <span className="text-[11px] text-muted-foreground w-20 shrink-0">Parent</span>
            <Link
              to={`/tasks/${parentTask.key}`}
              className="flex items-center gap-1.5 hover:underline min-w-0"
            >
              <TaskTypeIcon typeKey={parentTask.task_type?.key ?? 'task'} color={parentTask.task_type?.color} size={12} />
              <span className="font-medium shrink-0">{parentTask.key}</span>
              <span className="text-muted-foreground truncate">{parentTask.title}</span>
            </Link>
          </div>
        )}
      </div>
    </div>
  )

  const descriptionBlock = (
    <div className="space-y-2">
      <SectionLabel>Description</SectionLabel>
      {editingDesc ? (
        <div className="space-y-2">
          <textarea
            autoFocus
            value={descDraft}
            onChange={e => setDescDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Escape') setEditingDesc(false) }}
            onBlur={saveDesc}
            rows={Math.max(4, descDraft.split('\n').length + 1)}
            placeholder="Add a description…"
            className="w-full text-sm bg-transparent border border-border rounded-md px-3 py-2 outline-none focus:border-primary resize-none leading-relaxed"
          />
          <div className="flex gap-2">
            <Button size="sm" onMouseDown={e => e.preventDefault()} onClick={saveDesc}>Save</Button>
            <Button size="sm" variant="ghost"
              onMouseDown={e => e.preventDefault()}
              onClick={() => setEditingDesc(false)}
            >Cancel</Button>
          </div>
        </div>
      ) : (
        <div
          onClick={() => { setDescDraft(task.description ?? ''); setEditingDesc(true) }}
          className="cursor-text rounded-md px-2.5 py-2 -mx-2.5 hover:bg-muted/40 transition-colors min-h-10"
        >
          {task.description
            ? <p className="text-sm whitespace-pre-wrap leading-relaxed">{task.description}</p>
            : <p className="text-sm text-muted-foreground italic">Add a description…</p>}
        </div>
      )}
    </div>
  )

  const childTasksBlock = activeChildren.length > 0 && (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <SectionLabel>Child tasks ({activeChildren.length})</SectionLabel>
        <button
          onClick={() => setCreateChildOpen(true)}
          className="ml-auto p-0.5 rounded text-muted-foreground/50 hover:text-foreground hover:bg-muted transition-colors"
          title="Add child task"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            <line x1="7" y1="2" x2="7" y2="12" /><line x1="2" y1="7" x2="12" y2="7" />
          </svg>
        </button>
      </div>
      <ul className="rounded-lg border divide-y text-sm">
        {activeChildren.map(child => {
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
  )

  const linkTypeMap = new Map(linkTypes.map(lt => [lt.id, lt]))

  // All task IDs already linked (to exclude from search)
  const linkedTaskIds = new Set([
    task.id,
    ...taskLinks.map(l => l.source_task.id),
    ...taskLinks.map(l => l.target_task.id),
  ])

  const relationsBlock = (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <SectionLabel>Relations</SectionLabel>
        <button
          onClick={() => setLinkDialogOpen(true)}
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
        open={linkDialogOpen}
        onClose={() => setLinkDialogOpen(false)}
        taskId={task.id}
        excludeIds={linkedTaskIds}
      />
    </div>
  )

  const activityBlock = (
    <div className="space-y-3">
      <SectionLabel>Activity</SectionLabel>
      <div className="flex gap-0 border-b">
        {(['comments', 'history'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium capitalize border-b-2 -mb-px transition-colors',
              activeTab === tab
                ? 'border-primary text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground',
            )}
          >
            {tab === 'comments' ? `Comments (${comments.length})` : 'History'}
          </button>
        ))}
      </div>
      {activeTab === 'comments' && (
        <CommentSection taskId={task.id} currentUserId={currentUserId} userById={userById} />
      )}
      {activeTab === 'history' && (
        <p className="text-sm text-muted-foreground italic py-6 text-center">
          History coming soon.
        </p>
      )}
    </div>
  )

  const peopleBlock = (
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
              {task.reporter_id === currentUserId && (
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
          {task.reporter_id === currentUserId && members?.items && (
            <select
              className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-xs mt-1"
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
      </div>
    </div>
  )

  const fmtDate = (s: string) =>
    new Date(s).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' })

  const datesBlock = (
    <div className="space-y-2">
      <SectionLabel>Dates</SectionLabel>
      <div className="space-y-0.5 text-sm">
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Created</span>
          <span className="text-xs text-muted-foreground">{fmtDate(task.created_at)}</span>
        </div>
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Updated</span>
          <span className="text-xs text-muted-foreground">{fmtDate(task.updated_at)}</span>
        </div>

        {/* Start date */}
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Start date</span>
          {editingStartDate ? (
            <input
              type="date"
              autoFocus
              defaultValue={task.start_date ?? ''}
              className="text-xs border rounded px-1.5 py-0.5 bg-background"
              onChange={async e => {
                const val = e.target.value
                setEditingStartDate(false)
                await updateTask.mutateAsync({ start_date: val || null, version: task.version })
              }}
              onKeyDown={e => { if (e.key === 'Escape') setEditingStartDate(false) }}
              onBlur={() => setEditingStartDate(false)}
            />
          ) : (
            <div className="flex items-center gap-1">
              <button
                className="text-xs text-left hover:underline cursor-pointer text-muted-foreground hover:text-foreground"
                onClick={() => setEditingStartDate(true)}
              >
                {task.start_date ? fmtDate(task.start_date) : <span className="italic">Not set</span>}
              </button>
              {task.start_date && (
                <button
                  className="text-muted-foreground/40 hover:text-muted-foreground"
                  onClick={() => updateTask.mutateAsync({ start_date: null, version: task.version })}
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Due date */}
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Due date</span>
          {editingDueDate ? (
            <input
              type="date"
              autoFocus
              defaultValue={task.due_date ?? ''}
              className="text-xs border rounded px-1.5 py-0.5 bg-background"
              onChange={async e => {
                const val = e.target.value
                setEditingDueDate(false)
                await updateTask.mutateAsync({ due_date: val || null, version: task.version })
              }}
              onKeyDown={e => { if (e.key === 'Escape') setEditingDueDate(false) }}
              onBlur={() => setEditingDueDate(false)}
            />
          ) : (
            <div className="flex items-center gap-1">
              <button
                className="text-xs text-left hover:underline cursor-pointer text-muted-foreground hover:text-foreground"
                onClick={() => setEditingDueDate(true)}
              >
                {task.due_date ? fmtDate(task.due_date) : <span className="italic">Not set</span>}
              </button>
              {task.due_date && (
                <button
                  className="text-muted-foreground/40 hover:text-muted-foreground"
                  onClick={() => updateTask.mutateAsync({ due_date: null, version: task.version })}
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )

  const debugBlock = (
    <details className="border-t pt-4">
      <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/40 hover:text-muted-foreground select-none">
        Debug
      </summary>
      <div className="mt-3">
        <pre className="rounded-md bg-muted p-3 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
          {JSON.stringify(task, null, 2)}
        </pre>
      </div>
    </details>
  )

  // ── Layout ────────────────────────────────────────────────────────────────

  const modal = (
    <CreateTaskModal
      open={createChildOpen}
      projectId={task.project_id}
      parentTaskId={task.id}
      onClose={() => setCreateChildOpen(false)}
    />
  )

  if (mode === 'page') {
    return (
      <>
        <div className="space-y-5">
          {titleBlock}

          {(actionsBlock || confirmBackwardBlock) && (
            <div className="space-y-3 py-4 border-y">
              {actionsBlock}
              {confirmBackwardBlock}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] xl:grid-cols-[1fr_300px] gap-6 pt-1">
            <div className="min-w-0 space-y-6">
              {detailsBlock}
              {descriptionBlock}
              {childTasksBlock}
              {relationsBlock}
              {activityBlock}
              {debugBlock}
            </div>
            <div className="space-y-4">
              {peopleBlock}
              {datesBlock}
            </div>
          </div>
        </div>
        {modal}
      </>
    )
  }

  // panel
  return (
    <>
      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {titleBlock}
        {actionsBlock && <div className="py-3 border-y">{actionsBlock}</div>}
        {confirmBackwardBlock}
        {detailsBlock}
        {descriptionBlock}
        {childTasksBlock}
        {relationsBlock}
        {peopleBlock}
        {datesBlock}
        {activityBlock}
        {debugBlock}
      </div>
      {modal}
    </>
  )
}
