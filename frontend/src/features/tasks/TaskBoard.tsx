import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import type { AxiosError } from 'axios'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/AuthProvider'
import {
  useProjectTasks, useProjectWorkflows, useProjectResolutions, useProjectMembers,
  useTransitionStatus, type Status,
} from './api'
import { TaskCard } from './TaskCard'
import { TaskDetail } from './TaskDetail'
import { CreateTaskModal } from './CreateTaskModal'

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

export function TaskBoard() {
  const { id: projectId } = useParams<{ id: string }>()
  const { user } = useAuth()
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [dragOverCol, setDragOverCol] = useState<string | null>(null)
  const [boardError, setBoardError] = useState<string | null>(null)

  const { data: workflows, isLoading: wfLoading } = useProjectWorkflows(projectId ?? '')
  const { data: tasks, isLoading: tasksLoading } = useProjectTasks(projectId ?? '')
  const { data: resolutions = [] } = useProjectResolutions(projectId ?? '')
  const { data: membersData } = useProjectMembers(projectId)
  const transition = useTransitionStatus(projectId ?? '')

  const defaultWorkflow = workflows?.find(w => w.is_default) ?? workflows?.[0]
  const statuses: Status[] = useMemo(
    () => [...(defaultWorkflow?.statuses ?? [])].sort((a, b) => a.position - b.position),
    [defaultWorkflow],
  )
  const transitions = defaultWorkflow?.transitions ?? []

  const userById = useMemo(
    () => new Map(membersData?.items.map(m => [m.user.id, m.user]) ?? []),
    [membersData],
  )

  const activeTasks = useMemo(
    () => (tasks ?? []).filter(t => !t.deleted_at),
    [tasks],
  )

  const selectedTask = activeTasks.find(t => t.id === selectedTaskId) ?? null

  async function handleDrop(targetStatusId: string) {
    if (!draggedId) return
    const task = activeTasks.find(t => t.id === draggedId)
    if (!task || task.current_status_id === targetStatusId) {
      setDraggedId(null); setDragOverCol(null); return
    }
    setDraggedId(null); setDragOverCol(null); setBoardError(null)
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

  if (wfLoading || tasksLoading) return <BoardSkeleton />

  if (!defaultWorkflow) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-muted-foreground">
        No workflow configured for this project.
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-3 border-b px-5 py-3 shrink-0">
        <span className="text-sm text-muted-foreground">
          Board — <strong className="text-foreground">{activeTasks.length}</strong> tasks
        </span>
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
          {statuses.map(status => {
            const colTasks = activeTasks.filter(t => t.current_status_id === status.id)
            const isOver = dragOverCol === status.id
            return (
              <div key={status.id} className="flex flex-col w-[280px] shrink-0">
                <div className="flex items-center gap-2 pb-2.5 px-1">
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{
                      background: status.color ?? (
                        status.category === 'final' ? 'oklch(0.55 0.14 150)' :
                        status.category === 'initial' ? 'var(--muted-foreground)' :
                        'var(--primary)'
                      ),
                    }}
                  />
                  <span className="text-xs font-semibold uppercase tracking-wide">{status.name}</span>
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
                  onDragOver={e => { e.preventDefault(); setDragOverCol(status.id) }}
                  onDragLeave={e => {
                    const r = e.currentTarget.getBoundingClientRect()
                    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) {
                      setDragOverCol(null)
                    }
                  }}
                  onDrop={() => handleDrop(status.id)}
                  className={`flex flex-col gap-2 rounded-xl p-2 min-h-[120px] transition-colors ${
                    isOver
                      ? 'bg-primary/10 border-2 border-primary/40'
                      : 'bg-muted/50 border-2 border-transparent'
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
        </div>
      </div>

      <TaskDetail
        task={selectedTask}
        statuses={statuses}
        transitions={transitions}
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
