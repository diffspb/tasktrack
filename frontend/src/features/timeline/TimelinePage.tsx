import { useState } from 'react'
import { ViewMode } from 'gantt-task-react'
import { CalendarRange } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProjects } from '@/features/projects/api'
import { useGlobalTasks } from './api'
import { GanttChart } from './GanttChart'

export function TimelinePage() {
  const [viewMode, setViewMode] = useState<ViewMode>(ViewMode.Month)
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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b shrink-0">
        <CalendarRange className="h-5 w-5 text-primary" />
        <h1 className="text-base font-semibold">Timeline</h1>

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
        <main className="flex-1 overflow-auto p-4">
          {isLoading ? (
            <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
              Loading…
            </div>
          ) : (
            <GanttChart
              tasks={tasks}
              projects={visibleProjects}
              viewMode={viewMode}
            />
          )}
        </main>
      </div>
    </div>
  )
}
