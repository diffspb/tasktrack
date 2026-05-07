import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { useAuth } from '@/features/auth/AuthProvider'
import { useProjectTasks, useProjectWorkflows, useProjectMembers, type Task } from './api'
import { useProjectEvents, type TaskEvent } from './useProjectEvents'
import { useQueryClient } from '@tanstack/react-query'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

// ── Tree building ─────────────────────────────────────────────────────────────

interface TreeNode {
  task: Task
  depth: number
  hasChildren: boolean
}

function flattenVisible(
  tasks: Task[],
  expanded: Set<string>,
): TreeNode[] {
  const activeTasks = tasks.filter(t => !t.deleted_at)
  const childrenOf = new Map<string | null, Task[]>()

  for (const t of activeTasks) {
    const pid = t.parent_task_id ?? null
    if (!childrenOf.has(pid)) childrenOf.set(pid, [])
    childrenOf.get(pid)!.push(t)
  }

  // Sort: epics first, then by key within each group
  function sortedChildren(parentId: string | null) {
    return (childrenOf.get(parentId) ?? []).sort((a, b) => {
      const aIsEpic = a.task_type?.key === 'epic'
      const bIsEpic = b.task_type?.key === 'epic'
      if (aIsEpic !== bIsEpic) return aIsEpic ? -1 : 1
      return a.key.localeCompare(b.key, undefined, { numeric: true })
    })
  }

  const result: TreeNode[] = []

  function walk(parentId: string | null, depth: number) {
    for (const task of sortedChildren(parentId)) {
      const kids = childrenOf.get(task.id) ?? []
      result.push({ task, depth, hasChildren: kids.length > 0 })
      if (kids.length > 0 && expanded.has(task.id)) {
        walk(task.id, depth + 1)
      }
    }
  }

  walk(null, 0)
  return result
}

// ── Status badge ──────────────────────────────────────────────────────────────

function StatusBadge({ statusId, statusMap }: {
  statusId: string
  statusMap: Map<string, { name: string; category: string }>
}) {
  const s = statusMap.get(statusId)
  if (!s) return <span className="text-muted-foreground text-xs">—</span>
  const cls =
    s.category === 'final' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
    s.category === 'initial' ? 'bg-muted text-muted-foreground' :
    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
  return (
    <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium', cls)}>
      {s.name}
    </span>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  viewId: string
  projectId: string
}

export function EpicTreeView({ viewId: _viewId, projectId }: Props) {
  const { user } = useAuth()
  const qc = useQueryClient()

  const { data: tasks = [], isLoading: tasksLoading } = useProjectTasks(projectId)
  const { data: workflows = [], isLoading: wfLoading } = useProjectWorkflows(projectId)
  const { data: members } = useProjectMembers(projectId)

  // SSE live updates
  useProjectEvents(projectId, (evt: TaskEvent) => {
    if (evt.type === 'task.created') {
      qc.invalidateQueries({ queryKey: ['tasks', projectId] })
    } else if (evt.type === 'task.updated' || evt.type === 'task.status_changed') {
      qc.setQueryData<Task[]>(['tasks', projectId], old =>
        old?.map(t => t.id === evt.task_id ? evt.task! : t)
      )
    } else if (evt.type === 'task.deleted') {
      qc.setQueryData<Task[]>(['tasks', projectId], old =>
        old?.filter(t => t.id !== evt.task_id)
      )
    }
  })

  // Build status map from all workflows
  const statusMap = useMemo(() => {
    const m = new Map<string, { name: string; category: string }>()
    for (const wf of workflows) {
      for (const s of wf.statuses) m.set(s.id, s)
    }
    return m
  }, [workflows])

  const userById = useMemo(
    () => new Map(members?.items.map(m => [m.user.id, m.user]) ?? []),
    [members],
  )

  // Default: expand all epics
  const epicIds = useMemo(
    () => new Set(tasks.filter(t => t.task_type?.key === 'epic' && !t.deleted_at).map(t => t.id)),
    [tasks],
  )
  const [expanded, setExpanded] = useState<Set<string>>(epicIds)

  // Re-sync when new epics arrive (new project load)
  useMemo(() => {
    setExpanded(prev => {
      const next = new Set(prev)
      for (const id of epicIds) next.add(id)
      return next
    })
  }, [epicIds])

  const nodes = useMemo(() => flattenVisible(tasks, expanded), [tasks, expanded])

  function toggle(id: string) {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (tasksLoading || wfLoading) {
    return (
      <div className="p-5 space-y-2">
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-9 w-full" />)}
      </div>
    )
  }

  const INDENT = 20 // px per depth level
  const ICON_COL = 20 // type icon width
  const EXPAND_COL = 20 // expand button width

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center border-b px-4 py-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground shrink-0 bg-muted/30">
        <div className="flex-1">Task</div>
        <div className="w-36 shrink-0">Status</div>
        <div className="w-36 shrink-0">Assignee</div>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        {nodes.length === 0 ? (
          <div className="flex items-center justify-center py-24 text-sm text-muted-foreground">
            No tasks yet.
          </div>
        ) : (
          <ul className="divide-y">
            {nodes.map(({ task, depth, hasChildren }) => {
              const isExpanded = expanded.has(task.id)
              const typeColor = task.task_type?.color ?? '#6366f1'
              const assignee = task.assignee_id ? userById.get(task.assignee_id) : null
              const isMe = task.assignee_id === user?.id

              return (
                <li key={task.id} className="flex items-center gap-2 px-4 py-2 hover:bg-muted/40 transition-colors">
                  {/* Left: tree indent + expand + type icon + key + title */}
                  <div className="flex-1 flex items-center gap-1.5 min-w-0">
                    {/* indent */}
                    <div style={{ width: depth * INDENT }} className="shrink-0" />

                    {/* expand button — keeps space even when no children */}
                    <div style={{ width: EXPAND_COL }} className="shrink-0 flex items-center justify-center">
                      {hasChildren ? (
                        <button
                          onClick={() => toggle(task.id)}
                          className="rounded p-0.5 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                        >
                          {isExpanded
                            ? <ChevronDown className="h-3.5 w-3.5" />
                            : <ChevronRight className="h-3.5 w-3.5" />}
                        </button>
                      ) : null}
                    </div>

                    {/* type color dot */}
                    <div
                      style={{ width: ICON_COL, flexShrink: 0 }}
                      className="flex items-center justify-center"
                    >
                      <div
                        className="h-2 w-2 rounded-sm"
                        style={{ background: typeColor }}
                        title={task.task_type?.name ?? 'task'}
                      />
                    </div>

                    {/* key + title */}
                    <Link
                      to={`/tasks/${task.key}`}
                      className="font-mono text-[11px] font-semibold text-muted-foreground/70 hover:text-primary transition-colors shrink-0"
                    >
                      {task.key}
                    </Link>
                    <span className="text-sm truncate">{task.title}</span>
                  </div>

                  {/* Status — fixed width, aligned */}
                  <div className="w-36 shrink-0">
                    <StatusBadge statusId={task.current_status_id} statusMap={statusMap} />
                  </div>

                  {/* Assignee — fixed width, aligned */}
                  <div className="w-36 shrink-0 text-xs text-muted-foreground truncate">
                    {assignee
                      ? <span className={cn(isMe && 'font-semibold text-foreground')}>
                          {isMe ? 'You' : assignee.display_name}
                        </span>
                      : <span className="text-muted-foreground/40">—</span>}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
