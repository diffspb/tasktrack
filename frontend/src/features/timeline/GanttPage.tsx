import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ViewMode } from 'gantt-task-react'
import { ChevronLeft, ChevronRight, Plus, Settings, X, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuth } from '@/features/auth/AuthProvider'
import { useTaskByKey, type Task } from '@/features/tasks/api'
import { TaskDetail } from '@/features/tasks/TaskDetail'
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

function AddTaskWidget({ ganttId }: { ganttId: string }) {
  const [open, setOpen]   = useState(false)
  const [key, setKey]     = useState('')
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const lookupKey = key.trim().toUpperCase()
  const { data: found, isFetching } = useTaskByKey(lookupKey || null)
  const addMutation = useAddTaskToGantt(ganttId)

  async function handleAdd() {
    if (!found) return
    setError(null)
    try {
      await addMutation.mutateAsync(found.id)
      setKey('')
      setOpen(false)
    } catch {
      setError('Failed to add task')
    }
  }

  if (!open) {
    return (
      <Button
        variant="outline" size="sm" className="gap-1.5"
        onClick={() => { setOpen(true); setTimeout(() => inputRef.current?.focus(), 50) }}
      >
        <Plus className="h-3.5 w-3.5" /> Add task
      </Button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          ref={inputRef}
          value={key}
          onChange={e => { setKey(e.target.value); setError(null) }}
          onKeyDown={e => {
            if (e.key === 'Enter') handleAdd()
            if (e.key === 'Escape') setOpen(false)
          }}
          placeholder="Task key (e.g. DEMO-4)"
          className="h-8 pl-7 w-44 text-sm font-mono"
        />
      </div>
      {found && <span className="text-xs text-muted-foreground truncate max-w-40">{found.title}</span>}
      {isFetching && <span className="text-xs text-muted-foreground">…</span>}
      <Button size="sm" className="h-8 px-3" disabled={!found || addMutation.isPending} onClick={handleAdd}>
        Add
      </Button>
      <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => setOpen(false)}>
        <X className="h-3.5 w-3.5" />
      </Button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  )
}

export function GanttPage() {
  const { ganttId } = useParams<{ ganttId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [viewMode, setViewMode]       = useState<ViewMode>(ViewMode.Month)
  const [viewDate, setViewDate]       = useState<Date>(new Date())
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  const { data: gantt, isLoading: ganttLoading } = useGanttChart(ganttId)
  const { data: tasks = [], isLoading: tasksLoading } = useGanttTasks(ganttId)
  const removeTask = useRemoveTaskFromGantt(ganttId!)

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
          <AddTaskWidget ganttId={ganttId!} />
          <Button
            variant="ghost" size="sm" className="h-8 w-8 p-0"
            onClick={() => navigate(`/timeline/${ganttId}/settings`)}
          >
            <Settings className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Body: chart + side panel */}
      <div className="flex flex-1 overflow-hidden">
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-6">
          {tasksLoading ? (
            <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">Loading…</div>
          ) : (
            <GanttChart
              tasks={tasks}
              viewMode={viewMode}
              viewDate={viewDate}
              selectedTaskId={selectedTask?.id ?? null}
              onTaskSelect={t => setSelectedTask(prev => prev?.id === t.id ? null : t)}
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
        </main>

        {/* Side panel */}
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
