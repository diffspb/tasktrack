import { useState, useRef, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ViewMode } from 'gantt-task-react'
import { ChevronLeft, ChevronRight, Plus, Settings, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthProvider'
import { type Task } from '@/features/tasks/api'
import { TaskDetail } from '@/features/tasks/TaskDetail'
import { TaskSearchPopover } from '@/shared/ui/TaskSearchPopover'
import { useGanttChart, useGanttTasks, useAddTaskToGantt, useRemoveTaskFromGantt } from './ganttApi'
import { GanttChart } from './GanttChart'

function addMonths(d: Date, n: number): Date {
  const r = new Date(d)
  r.setMonth(r.getMonth() + n)
  return r
}

function addWeeks(d: Date, n: number): Date {
  return new Date(d.getTime() + n * 7 * 86_400_000)
}

export function GanttPage() {
  const { ganttId } = useParams<{ ganttId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [viewMode, setViewMode]         = useState<ViewMode>(ViewMode.Month)
  const [viewDate, setViewDate]         = useState<Date>(new Date())
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [chartAreaWidth, setChartAreaWidth] = useState(0)
  const chartAreaRef = useRef<HTMLDivElement>(null)

  // Measure the chart area (the direct flex sibling of TaskDetail) to get the
  // correct available width — this element is properly constrained by the sidebar.
  useEffect(() => {
    const el = chartAreaRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => setChartAreaWidth(entry.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const { data: gantt, isLoading: ganttLoading } = useGanttChart(ganttId)
  const { data: tasks = [], isLoading: tasksLoading } = useGanttTasks(ganttId)
  const removeTask = useRemoveTaskFromGantt(ganttId!)
  const addTask    = useAddTaskToGantt(ganttId!)

  const addedTaskIds = new Set(tasks.map(t => t.id))

  function stepBack() {
    setViewDate(prev => viewMode === ViewMode.Week ? addWeeks(prev, -4) : addMonths(prev, -3))
  }
  function stepForward() {
    setViewDate(prev => viewMode === ViewMode.Week ? addWeeks(prev, 4) : addMonths(prev, 3))
  }

  const rootTaskIds = new Set(
    tasks.filter(t => !tasks.some(p => p.id === t.parent_task_id)).map(t => t.id)
  )

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

        {/* Time navigation */}
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

        {/* Zoom */}
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
            variant="ghost" size="sm" className="h-8 w-8 p-0"
            onClick={() => navigate(`/timeline/${ganttId}/settings`)}
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Body: chart + side panel — mirrors TaskBacklog layout */}
      <div ref={chartAreaRef} className="flex flex-1 min-h-0 overflow-hidden">
        {/* Left: chart area (flex-col wrapper prevents scrollbar from affecting flex-row layout) */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          <div className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-4 space-y-6">
            {tasksLoading ? (
              <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">Loading…</div>
            ) : (
              <GanttChart
                tasks={tasks}
                viewMode={viewMode}
                viewDate={viewDate}
                selectedTaskId={selectedTask?.id ?? null}
                onTaskSelect={t => setSelectedTask(prev => prev?.id === t.id ? null : t)}
                containerWidth={chartAreaWidth}
              />
            )}

            {/* Added root tasks — remove chips */}
            {tasks.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  Added tasks ({rootTaskIds.size})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {tasks.filter(t => rootTaskIds.has(t.id)).map(t => (
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
