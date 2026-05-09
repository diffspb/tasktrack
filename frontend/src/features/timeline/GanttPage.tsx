import { useState, useRef, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ViewMode } from 'gantt-task-react'
import { ChevronLeft, ChevronRight, Plus, Settings, X, ListOrdered, GripVertical } from 'lucide-react'
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthProvider'
import { type Task } from '@/features/tasks/api'
import { TaskDetail } from '@/features/tasks/TaskDetail'
import { TaskTypeIcon } from '@/features/tasks/TaskTypeIcon'
import { TaskSearchPopover } from '@/shared/ui/TaskSearchPopover'
import { cn } from '@/lib/utils'
import {
  useGanttChart, useGanttTasks, useGanttLinks,
  useAddTaskToGantt, useRemoveTaskFromGantt, useReorderGanttTasks,
} from './ganttApi'
import { GanttChart } from './GanttChart'

function addMonths(d: Date, n: number): Date {
  const r = new Date(d)
  r.setMonth(r.getMonth() + n)
  return r
}

function addWeeks(d: Date, n: number): Date {
  return new Date(d.getTime() + n * 7 * 86_400_000)
}

// ── Sortable row ──────────────────────────────────────────────────────────────

function SortableItem({ task, onRemove }: { task: Task; onRemove: () => void }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: task.id })
  const style = { transform: CSS.Transform.toString(transform), transition }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-sm select-none',
        isDragging && 'opacity-40 shadow-lg',
      )}
    >
      <button
        className="cursor-grab text-muted-foreground hover:text-foreground shrink-0 touch-none"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="shrink-0">
        <TaskTypeIcon
          typeKey={task.task_type?.key ?? 'task'}
          color={task.task_type?.color ?? '#6366f1'}
          size={14}
        />
      </div>
      <span className="font-mono text-xs text-muted-foreground shrink-0">{task.key}</span>
      <span className="flex-1 truncate text-foreground/90">{task.title}</span>
      <button
        className="text-muted-foreground/40 hover:text-destructive shrink-0"
        onClick={onRemove}
        title="Remove from gantt"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function GanttPage() {
  const { ganttId } = useParams<{ ganttId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [viewMode, setViewMode]         = useState<ViewMode>(ViewMode.Month)
  const [viewDate, setViewDate]         = useState<Date>(new Date())
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [chartAreaWidth, setChartAreaWidth] = useState(0)
  const [sortMode, setSortMode]         = useState(false)
  const [sortOrder, setSortOrder]       = useState<string[]>([])
  const chartAreaRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = chartAreaRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => setChartAreaWidth(entry.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const { data: gantt, isLoading: ganttLoading } = useGanttChart(ganttId)
  const { data: tasks = [], isLoading: tasksLoading } = useGanttTasks(ganttId)
  const { data: links = [] } = useGanttLinks(ganttId)
  const removeTask    = useRemoveTaskFromGantt(ganttId!)
  const addTask       = useAddTaskToGantt(ganttId!)
  const reorderTasks  = useReorderGanttTasks(ganttId!)

  const addedTaskIds = new Set(tasks.map(t => t.id))
  const rootTaskIds  = new Set(
    tasks.filter(t => !tasks.some(p => p.id === t.parent_task_id)).map(t => t.id)
  )
  const rootTasks = tasks.filter(t => rootTaskIds.has(t.id))
  const taskMap   = new Map(tasks.map(t => [t.id, t]))

  const sensors = useSensors(useSensor(PointerSensor))

  function toggleSortMode() {
    if (!sortMode) setSortOrder(rootTasks.map(t => t.id))
    setSortMode(v => !v)
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    setSortOrder(prev => {
      const oldIdx = prev.indexOf(String(active.id))
      const newIdx = prev.indexOf(String(over.id))
      const next = arrayMove(prev, oldIdx, newIdx)
      reorderTasks.mutate(next)
      return next
    })
  }

  const handleRemoveInSort = useCallback((taskId: string) => {
    removeTask.mutate(taskId)
    setSortOrder(prev => prev.filter(id => id !== taskId))
  }, [removeTask])

  function stepBack() {
    setViewDate(prev => viewMode === ViewMode.Week ? addWeeks(prev, -4) : addMonths(prev, -3))
  }
  function stepForward() {
    setViewDate(prev => viewMode === ViewMode.Week ? addWeeks(prev, 4) : addMonths(prev, 3))
  }

  if (ganttLoading) return <div className="p-8 text-sm text-muted-foreground">Loading…</div>
  if (!gantt) return null

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-3 border-b shrink-0">
        <h1 className="text-base font-semibold truncate">{gantt.name}</h1>
        {gantt.description && (
          <span className="text-xs text-muted-foreground hidden sm:block truncate">{gantt.description}</span>
        )}

        {/* Time navigation — hidden in sort mode */}
        {!sortMode && (
          <>
            <div className="flex items-center gap-1 ml-2 shrink-0">
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={stepBack}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={() => setViewDate(new Date())}>
                Today
              </Button>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={stepForward}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex items-center gap-1 rounded-md border p-0.5 bg-muted/30 shrink-0">
              {([ViewMode.Week, ViewMode.Month] as const).map(mode => (
                <Button
                  key={mode}
                  variant={viewMode === mode ? 'secondary' : 'ghost'}
                  size="sm"
                  className="h-6 px-2.5 text-xs"
                  onClick={() => setViewMode(mode)}
                >
                  {mode}
                </Button>
              ))}
            </div>
          </>
        )}

        {sortMode && (
          <span className="ml-2 text-xs text-muted-foreground">Drag to reorder tasks</span>
        )}

        <div className="ml-auto flex items-center gap-2 shrink-0">
          <TaskSearchPopover
            excludeIds={addedTaskIds}
            onSelect={task => addTask.mutate(task.id)}
            trigger={
              <Button variant="outline" size="sm" className="gap-1.5">
                <Plus className="h-3.5 w-3.5" /> Add task
              </Button>
            }
          />
          <Button
            variant={sortMode ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 w-8 p-0"
            onClick={toggleSortMode}
            title="Reorder tasks"
          >
            <ListOrdered className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost" size="sm" className="h-8 w-8 p-0"
            onClick={() => navigate(`/timeline/${ganttId}/settings`)}
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Body */}
      <div ref={chartAreaRef} className="flex flex-1 min-h-0 overflow-hidden">
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 space-y-6">

            {sortMode ? (
              /* Sort mode: drag-and-drop list, no gantt */
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                <SortableContext items={sortOrder} strategy={verticalListSortingStrategy}>
                  <div className="space-y-1.5 max-w-2xl">
                    {sortOrder.map(id => {
                      const task = taskMap.get(id)
                      if (!task) return null
                      return (
                        <SortableItem
                          key={id}
                          task={task}
                          onRemove={() => handleRemoveInSort(task.id)}
                        />
                      )
                    })}
                    {sortOrder.length === 0 && (
                      <p className="text-sm text-muted-foreground py-8 text-center">No tasks added yet.</p>
                    )}
                  </div>
                </SortableContext>
              </DndContext>
            ) : (
              /* Normal mode: gantt chart + chips */
              <>
                {tasksLoading ? (
                  <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">Loading…</div>
                ) : (
                  <GanttChart
                    tasks={tasks}
                    links={links}
                    viewMode={viewMode}
                    viewDate={viewDate}
                    selectedTaskId={selectedTask?.id ?? null}
                    onTaskSelect={t => setSelectedTask(prev => prev?.id === t.id ? null : t)}
                    containerWidth={chartAreaWidth}
                  />
                )}

                {rootTasks.length > 0 && (
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                      Added tasks ({rootTaskIds.size})
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {rootTasks.map(t => (
                        <div key={t.id} className="flex items-center gap-1 rounded border px-2 py-1 text-xs bg-muted/30">
                          <span className="font-mono text-muted-foreground">{t.key}</span>
                          <span className="truncate max-w-32">{t.title}</span>
                          <button
                            className="ml-1 text-muted-foreground/50 hover:text-destructive"
                            onClick={() => removeTask.mutate(t.id)}
                            title="Remove from gantt"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Right: task detail panel */}
        <TaskDetail
          task={selectedTask}
          projectId={selectedTask?.project_id ?? ''}
          currentUserId={user?.id ?? ''}
          onClose={() => setSelectedTask(null)}
        />
      </div>
    </div>
  )
}
