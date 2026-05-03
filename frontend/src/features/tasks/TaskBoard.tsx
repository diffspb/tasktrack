import { useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import type { AxiosError } from 'axios'
import { Plus, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/AuthProvider'
import {
  useProjectTasks, useProjectWorkflows, useProjectResolutions, useProjectMembers,
  useTransitionStatus, type Task,
} from './api'
import { useBoardColumns, type BoardColumn } from '@/features/projects/workflowApi'
import { TaskCard } from './TaskCard'
import { TaskDetail } from './TaskDetail'
import { CreateTaskModal } from './CreateTaskModal'
import { TaskFilterBar, DEFAULT_FILTER, applyFilter, type FilterState } from './TaskFilter'

function BoardSkeleton() {
  return (
    <div className="flex gap-4 p-5">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="w-[280px] shrink-0 space-y-3">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-20 w-full rounded-xl" />
        </div>
      ))}
    </div>
  )
}

function isDropTarget(
  column: BoardColumn,
  draggedTask: Task | undefined,
  allTransitions: { from_status_id: string; to_status_id: string }[],
): boolean {
  if (!draggedTask) return false
  return column.status_ids.some(targetId =>
    allTransitions.some(
      t => t.from_status_id === draggedTask.current_status_id && t.to_status_id === targetId,
    )
  )
}

export function TaskBoard() {
  const { id: projectId } = useParams<{ id: string }>()
  const { user } = useAuth()
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [filter, setFilter] = useState<FilterState>(DEFAULT_FILTER)
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [dragOverCol, setDragOverCol] = useState<string | null>(null)
  const [boardError, setBoardError] = useState<string | null>(null)

  const { data: boardColumnsData, isLoading: bcLoading } = useBoardColumns(projectId)
  const { data: workflows, isLoading: wfLoading } = useProjectWorkflows(projectId ?? '')
  const { data: tasks, isLoading: tasksLoading } = useProjectTasks(projectId ?? '')
  const { data: resolutions = [] } = useProjectResolutions(projectId ?? '')
  const { data: membersData } = useProjectMembers(projectId)
  const transition = useTransitionStatus(projectId ?? '')

  const columns = useMemo(
    () => [...(boardColumnsData?.items ?? [])].sort((a, b) => a.position - b.position),
    [boardColumnsData],
  )

  const allTransitions = useMemo(
    () => (workflows ?? []).flatMap(wf => wf.transitions),
    [workflows],
  )

  const allStatuses = useMemo(
    () => (workflows ?? []).flatMap(wf => wf.statuses),
    [workflows],
  )

  const userById = useMemo(
    () => new Map(membersData?.items.map(m => [m.user.id, m.user]) ?? []),
    [membersData],
  )

  const allActive = useMemo(() => (tasks ?? []).filter(t => !t.deleted_at), [tasks])
  const taskById = useMemo(() => new Map(allActive.map(t => [t.id, t])), [allActive])
  const activeTasks = useMemo(
    () => applyFilter(allActive, filter, user?.id ?? ''),
    [allActive, filter, user?.id],
  )

  const draggedTask = draggedId ? taskById.get(draggedId) : undefined

  // Tasks whose current_status_id is not in any board column
  const mappedStatusIds = useMemo(
    () => new Set(columns.flatMap(c => c.status_ids)),
    [columns],
  )
  const unmappedTasks = activeTasks.filter(t => !mappedStatusIds.has(t.current_status_id))

  const selectedTask = activeTasks.find(t => t.id === selectedTaskId) ?? null

  async function handleDrop(targetColumn: BoardColumn) {
    if (!draggedId) return
    const task = taskById.get(draggedId)
    if (!task) { setDraggedId(null); setDragOverCol(null); return }

    const targetStatusId = targetColumn.status_ids.find(sid =>
      allTransitions.some(t => t.from_status_id === task.current_status_id && t.to_status_id === sid)
    )

    setDraggedId(null); setDragOverCol(null)

    if (!targetStatusId) {
      if (task.current_status_id !== targetColumn.status_ids[0]) {
        showError('That transition is not allowed in this workflow.')
      }
      return
    }

    setBoardError(null)
    try {
      await transition.mutateAsync({ taskId: task.id, status_id: targetStatusId })
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      if (code === 'RESOLUTION_REQUIRED') {
        setSelectedTaskId(task.id)
      } else if (code === 'WORKFLOW_TRANSITION_NOT_ALLOWED') {
        showError('That transition is not allowed in this workflow.')
      } else if (code === 'TASK_BLOCKED_BY_SUBTASKS') {
        showError('Task is blocked: subtasks are not resolved yet.')
      } else {
        showError('Failed to move task.')
      }
    }
  }

  function showError(msg: string) {
    setBoardError(msg)
    setTimeout(() => setBoardError(null), 4000)
  }

  if (bcLoading || wfLoading || tasksLoading) return <BoardSkeleton />

  if (columns.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-24 text-sm text-muted-foreground">
        <p>No board columns configured for this project.</p>
        <Link
          to={`/projects/${projectId}/settings/board`}
          className="inline-flex items-center gap-1.5 rounded-md border border-input bg-background px-3 py-1.5 text-sm font-medium shadow-sm hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          <Settings className="h-3.5 w-3.5" />
          Configure board columns
        </Link>
      </div>
    )
  }

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center gap-3 border-b px-5 py-3 shrink-0">
          <TaskFilterBar filter={filter} onChange={setFilter} taskCount={activeTasks.length} />
          <div className="flex-1" />
          {boardError && <span className="text-sm text-destructive">{boardError}</span>}
          <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            Create task
          </Button>
        </div>

        {/* Kanban columns */}
        <div className="flex-1 overflow-x-auto overflow-y-hidden">
          <div className="flex gap-4 p-5 h-full items-start">
            {columns.map(col => {
              const colTasks = activeTasks.filter(t => col.status_ids.includes(t.current_status_id))
              const allowed = isDropTarget(col, draggedTask, allTransitions)
              const isOver = dragOverCol === col.id

              const headerStatus = allStatuses.find(s => col.status_ids.includes(s.id))

              return (
                <div key={col.id} className="flex flex-col w-[280px] shrink-0">
                  <div className="flex items-center gap-2 pb-2.5 px-1">
                    <div
                      className="h-2 w-2 rounded-full"
                      style={{
                        background: headerStatus?.color ?? 'var(--muted-foreground)',
                      }}
                    />
                    <span className="text-xs font-semibold uppercase tracking-wide">{col.name}</span>
                    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[11px] font-semibold text-muted-foreground">
                      {colTasks.length}
                    </span>
                    <div className="flex-1" />
                    <button
                      onClick={() => setCreateOpen(true)}
                      className="rounded p-0.5 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground transition-colors"
                    >
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  <div
                    onDragOver={e => { e.preventDefault(); setDragOverCol(col.id) }}
                    onDragLeave={e => {
                      const r = e.currentTarget.getBoundingClientRect()
                      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) {
                        setDragOverCol(null)
                      }
                    }}
                    onDrop={() => handleDrop(col)}
                    className={`flex flex-col gap-2 rounded-xl p-2 min-h-[120px] transition-all border-2 ${
                      draggedId
                        ? allowed
                          ? isOver
                            ? 'bg-primary/10 border-primary/40'
                            : 'bg-primary/5 border-primary/20'
                          : 'opacity-40 border-transparent bg-muted/30'
                        : isOver
                          ? 'bg-primary/10 border-primary/40'
                          : 'bg-muted/50 border-transparent'
                    }`}
                  >
                    {colTasks.length === 0 && !isOver && (
                      <div className="flex items-center justify-center py-8 text-xs text-muted-foreground/40">
                        No tasks
                      </div>
                    )}
                    {colTasks.map(task => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        assigneeName={task.assignee_id ? userById.get(task.assignee_id)?.display_name : undefined}
                        epicKey={task.parent_task_id ? taskById.get(task.parent_task_id)?.key : undefined}
                        isDragging={draggedId === task.id}
                        onClick={() => setSelectedTaskId(task.id)}
                        onDragStart={() => setDraggedId(task.id)}
                        onDragEnd={() => { setDraggedId(null); setDragOverCol(null) }}
                      />
                    ))}
                    {isOver && draggedId && !colTasks.find(t => t.id === draggedId) && (
                      <div className="rounded-lg border-2 border-dashed border-primary/40 h-16 flex items-center justify-center">
                        <span className="text-xs text-primary/60 font-medium">Drop here</span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {/* Uncategorized column for tasks without board column mapping */}
            {unmappedTasks.length > 0 && (
              <div className="flex flex-col w-[280px] shrink-0 opacity-60">
                <div className="flex items-center gap-2 pb-2.5 px-1">
                  <div className="h-2 w-2 rounded-full bg-muted-foreground/40" />
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Uncategorized
                  </span>
                  <span className="rounded-full bg-muted px-1.5 py-0.5 text-[11px] font-semibold text-muted-foreground">
                    {unmappedTasks.length}
                  </span>
                </div>
                <div className="flex flex-col gap-2 rounded-xl p-2 min-h-[120px] bg-muted/30 border-2 border-dashed border-muted-foreground/20">
                  {unmappedTasks.map(task => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      assigneeName={task.assignee_id ? userById.get(task.assignee_id)?.display_name : undefined}
                      epicKey={task.parent_task_id ? taskById.get(task.parent_task_id)?.key : undefined}
                      isDragging={false}
                      onClick={() => setSelectedTaskId(task.id)}
                      onDragStart={() => {}}
                      onDragEnd={() => {}}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <TaskDetail
        task={selectedTask}
        statuses={allStatuses}
        transitions={allTransitions}
        resolutions={resolutions}
        projectId={projectId ?? ''}
        currentUserId={user?.id ?? ''}
        onClose={() => setSelectedTaskId(null)}
      />

      <CreateTaskModal
        open={createOpen}
        projectId={projectId ?? ''}
        onClose={() => setCreateOpen(false)}
      />
    </div>
  )
}
