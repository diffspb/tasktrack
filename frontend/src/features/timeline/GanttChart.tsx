import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Gantt, ViewMode } from 'gantt-task-react'
import type { Task as GanttTask } from 'gantt-task-react'
import 'gantt-task-react/dist/index.css'
import type { Task } from '@/features/tasks/api'
import type { Project } from '@/features/projects/api'

const TYPE_COLORS: Record<string, string> = {
  bug:      '#ef4444',
  story:    '#10b981',
  epic:     '#f59e0b',
  decision: '#8b5cf6',
  task:     '#6366f1',
}

const PROJECT_COLORS = [
  '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6',
]

function projectColor(key: string): string {
  let h = 0
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) & 0xffff
  return PROJECT_COLORS[h % PROJECT_COLORS.length]
}

function toDate(s: string): Date {
  const d = new Date(s)
  d.setHours(0, 0, 0, 0)
  return d
}

function addDay(d: Date, n = 1): Date {
  return new Date(d.getTime() + n * 86_400_000)
}

interface Props {
  tasks: Task[]
  projects: Project[]
  viewMode: ViewMode
}

export function GanttChart({ tasks, projects, viewMode }: Props) {
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  const ganttTasks = useMemo<GanttTask[]>(() => {
    const rows: GanttTask[] = []

    for (const project of projects) {
      const projectTasks = tasks.filter(t => t.project_id === project.id)
      if (!projectTasks.length) continue

      const color = projectColor(project.key)
      const epics = projectTasks.filter(t => t.task_type?.key === 'epic')
      const topLevel = projectTasks.filter(t => t.task_type?.key !== 'epic')

      // Compute project date range from all scheduled tasks
      const scheduled = projectTasks.filter(t => t.start_date)
      const projStart = scheduled.length
        ? new Date(Math.min(...scheduled.map(t => toDate(t.start_date!).getTime())))
        : new Date()
      const projEnd = scheduled.length
        ? new Date(Math.max(...scheduled.map(t =>
            toDate(t.due_date ?? t.start_date!).getTime()
          )))
        : addDay(new Date())

      const projId = `proj-${project.id}`
      rows.push({
        id: projId,
        name: `${project.key}  ${project.name}`,
        type: 'project',
        start: projStart,
        end: projEnd < projStart ? addDay(projStart) : projEnd,
        progress: 0,
        hideChildren: collapsed.has(projId),
        styles: {
          backgroundColor: color + '33',
          progressColor: color,
          backgroundSelectedColor: color + '55',
        },
      })

      if (collapsed.has(projId)) continue

      // Tasks under epics
      for (const epic of epics) {
        const children = projectTasks.filter(t => t.parent_task_id === epic.id)
        const epicScheduled = [epic, ...children].filter(t => t.start_date)
        const epicStart = epicScheduled.length
          ? new Date(Math.min(...epicScheduled.map(t => toDate(t.start_date!).getTime())))
          : projStart
        const epicEnd = epicScheduled.length
          ? new Date(Math.max(...epicScheduled.map(t =>
              toDate(t.due_date ?? t.start_date!).getTime()
            )))
          : addDay(epicStart)

        const epicId = `epic-${epic.id}`
        rows.push({
          id: epicId,
          name: epic.title,
          type: 'project',
          project: projId,
          start: epicStart,
          end: epicEnd <= epicStart ? addDay(epicStart) : epicEnd,
          progress: 0,
          hideChildren: collapsed.has(epicId),
          styles: {
            backgroundColor: '#f59e0b33',
            progressColor: '#f59e0b',
            backgroundSelectedColor: '#f59e0b55',
          },
        })

        if (collapsed.has(epicId)) continue

        for (const child of children) {
          if (!child.start_date) continue
          const barColor = TYPE_COLORS[child.task_type?.key ?? 'task'] ?? '#6366f1'
          const start = toDate(child.start_date)
          const end = child.due_date ? toDate(child.due_date) : addDay(start)
          rows.push({
            id: child.id,
            name: child.title,
            type: 'task',
            project: epicId,
            start,
            end: end <= start ? addDay(start) : end,
            progress: 0,
            styles: {
              backgroundColor: barColor + 'aa',
              progressColor: barColor,
              backgroundSelectedColor: barColor,
            },
          })
        }
      }

      // Top-level tasks (not epics, not children of epics)
      const epicChildIds = new Set(epics.flatMap(e =>
        projectTasks.filter(t => t.parent_task_id === e.id).map(t => t.id)
      ))
      for (const t of topLevel) {
        if (epicChildIds.has(t.id) || !t.start_date) continue
        const barColor = TYPE_COLORS[t.task_type?.key ?? 'task'] ?? '#6366f1'
        const start = toDate(t.start_date)
        const end = t.due_date ? toDate(t.due_date) : addDay(start)
        rows.push({
          id: t.id,
          name: t.title,
          type: 'task',
          project: projId,
          start,
          end: end <= start ? addDay(start) : end,
          progress: 0,
          styles: {
            backgroundColor: barColor + 'aa',
            progressColor: barColor,
            backgroundSelectedColor: barColor,
          },
        })
      }
    }

    return rows
  }, [tasks, projects, collapsed])

  if (!ganttTasks.length) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        No tasks with scheduled dates found.
      </div>
    )
  }

  const unscheduled = tasks.filter(t => !t.start_date).length

  return (
    <div className="flex flex-col gap-2">
      {unscheduled > 0 && (
        <p className="text-xs text-muted-foreground px-1">
          {unscheduled} task{unscheduled !== 1 ? 's' : ''} without a start date are not shown.
        </p>
      )}
      <div className="rounded-lg border overflow-hidden">
        <Gantt
          tasks={ganttTasks}
          viewMode={viewMode}
          locale="en-GB"
          listCellWidth="200px"
          columnWidth={viewMode === ViewMode.Week ? 120 : 65}
          rowHeight={36}
          headerHeight={48}
          barFill={65}
          barCornerRadius={4}
          todayColor="rgba(99,102,241,0.15)"
          fontFamily="inherit"
          fontSize="12px"
          onClick={task => {
            // Navigate only for leaf tasks (type='task'), not project/epic groups
            if (task.type === 'task') {
              const found = tasks.find(t => t.id === task.id)
              if (found) navigate(`/tasks/${found.key}`)
            }
          }}
          onExpanderClick={task => {
            setCollapsed(prev => {
              const next = new Set(prev)
              if (next.has(task.id)) next.delete(task.id)
              else next.add(task.id)
              return next
            })
          }}
        />
      </div>
    </div>
  )
}
