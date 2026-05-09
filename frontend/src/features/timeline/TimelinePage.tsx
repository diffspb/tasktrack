import { useState } from 'react'
import { ViewMode } from 'gantt-task-react'
import { CalendarRange, ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProjects } from '@/features/projects/api'
import { useGlobalTasks } from './api'
import { GanttChart } from './GanttChart'

function addMonths(d: Date, n: number): Date {
  const r = new Date(d)
  r.setMonth(r.getMonth() + n)
  return r
}

function addWeeks(d: Date, n: number): Date {
  return new Date(d.getTime() + n * 7 * 86_400_000)
}

function fmtPeriod(d: Date, mode: ViewMode): string {
  if (mode === ViewMode.Week) {
    return d.toLocaleDateString('en', { month: 'short', year: 'numeric' })
  }
  return d.toLocaleDateString('en', { month: 'long', year: 'numeric' })
}

export function TimelinePage() {
  const [viewMode, setViewMode] = useState<ViewMode>(ViewMode.Month)
  const [viewDate, setViewDate] = useState<Date>(new Date())
  const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([])

  const { data: projects = [] } = useProjects()
  const filterIds = selectedProjectIds.length ? selectedProjectIds : undefined
  const { data: tasks = [], isLoading } = useGlobalTasks(filterIds)

  const visibleProjects = selectedProjectIds.length
    ? projects.filter(p => selectedProjectIds.includes(p.id))
    : projects

  function toggleProject(id: string) {
    setSelectedProjectIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  function stepBack() {
    setViewDate(prev =>
      viewMode === ViewMode.Week ? addWeeks(prev, -4) : addMonths(prev, -3)
    )
  }

  function stepForward() {
    setViewDate(prev =>
      viewMode === ViewMode.Week ? addWeeks(prev, 4) : addMonths(prev, 3)
    )
  }

  function goToday() {
    setViewDate(new Date())
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b shrink-0">
        <CalendarRange className="h-5 w-5 text-primary" />
        <h1 className="text-base font-semibold">Timeline</h1>

        {/* Time navigation */}
        <div className="flex items-center gap-1 ml-4">
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={stepBack}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={goToday}>
            Today
          </Button>
          <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={stepForward}>
            <ChevronRight className="h-4 w-4" />
          </Button>
          <span className="text-xs text-muted-foreground ml-1 min-w-24">
            {fmtPeriod(viewDate, viewMode)}
          </span>
        </div>

        {/* Zoom toggle */}
        <div className="ml-auto flex items-center gap-1 rounded-md border p-0.5 bg-muted/30">
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
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Project filter sidebar */}
        <aside className="w-44 shrink-0 border-r px-3 py-4 overflow-y-auto">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-2">
            Projects
          </p>
          <div className="space-y-0.5">
            <button
              className={`w-full text-left px-2 py-1 rounded text-xs transition-colors ${
                !selectedProjectIds.length
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:text-foreground hover:bg-muted'
              }`}
              onClick={() => setSelectedProjectIds([])}
            >
              All projects
            </button>
            {projects.map(p => (
              <button
                key={p.id}
                className={`w-full text-left px-2 py-1 rounded text-xs transition-colors ${
                  selectedProjectIds.includes(p.id)
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
                onClick={() => toggleProject(p.id)}
              >
                <span className="font-mono mr-1 text-[10px]">{p.key}</span>
                {p.name}
              </button>
            ))}
          </div>
        </aside>

        {/* Chart area */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-4">
          {isLoading ? (
            <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
              Loading…
            </div>
          ) : (
            <GanttChart
              tasks={tasks}
              projects={visibleProjects}
              viewMode={viewMode}
              viewDate={viewDate}
            />
          )}
        </main>
      </div>
    </div>
  )
}
