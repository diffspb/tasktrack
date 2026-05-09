import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Gantt, ViewMode } from 'gantt-task-react'
import type { Task as GanttTask } from 'gantt-task-react'
import 'gantt-task-react/dist/index.css'
import type { Task } from '@/features/tasks/api'

const TYPE_COLORS: Record<string, string> = {
  bug:      '#ef4444',
  story:    '#10b981',
  epic:     '#f59e0b',
  decision: '#8b5cf6',
  task:     '#6366f1',
}

function addDays(d: Date, n: number): Date {
  return new Date(d.getTime() + n * 86_400_000)
}

function toDate(s: string): Date {
  const d = new Date(s)
  d.setHours(0, 0, 0, 0)
  return d
}

/** Resolve effective start date: start_date ?? created_at */
function resolveStart(task: Task): Date {
  return toDate(task.start_date ?? task.created_at)
}

/**
 * Resolve effective end date using priority:
 * 1. start + duration_days
 * 2. task.due_date
 * 3. max(children end dates) recursively
 * 4. start + 1 day
 */
function resolveEnd(task: Task, allTasks: Task[]): Date {
  const start = resolveStart(task)

  if (task.duration_days) {
    return addDays(start, task.duration_days)
  }

  if (task.due_date) {
    const end = toDate(task.due_date)
    return end > start ? end : addDays(start, 1)
  }

  const children = allTasks.filter(t => t.parent_task_id === task.id)
  if (children.length > 0) {
    const maxEnd = new Date(Math.max(...children.map(c => resolveEnd(c, allTasks).getTime())))
    if (maxEnd > start) return maxEnd
  }

  return addDays(start, 1)
}

interface Props {
  tasks: Task[]
  viewMode: ViewMode
  viewDate?: Date
}

export function GanttChart({ tasks, viewMode, viewDate }: Props) {
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())

  const ganttTasks = useMemo<GanttTask[]>(() => {
    const rows: GanttTask[] = []

    // Group: root tasks first, then their children
    const roots = tasks.filter(t => !tasks.some(p => p.id === t.parent_task_id))
    const taskMap = new Map(tasks.map(t => [t.id, t]))

    function addTask(task: Task, parentGanttId?: string) {
      const start = resolveStart(task)
      const end = resolveEnd(task, tasks)
      const color = TYPE_COLORS[task.task_type?.key ?? 'task'] ?? '#6366f1'
      const children = tasks.filter(t => t.parent_task_id === task.id)
      const hasChildren = children.length > 0
      const ganttId = task.id

      rows.push({
        id: ganttId,
        name: task.title,
        type: hasChildren ? 'project' : 'task',
        project: parentGanttId,
        start,
        end: end <= start ? addDays(start, 1) : end,
        progress: 0,
        hideChildren: collapsed.has(ganttId),
        styles: hasChildren
          ? {
              backgroundColor: color + '22',
              progressColor: color,
              backgroundSelectedColor: color + '44',
            }
          : {
              backgroundColor: color + 'bb',
              progressColor: color,
              backgroundSelectedColor: color,
            },
      })

      if (!collapsed.has(ganttId)) {
        for (const child of children) {
          addTask(child, ganttId)
        }
      }
    }

    for (const root of roots) {
      // Only add if root is actually in the fetched list (it should always be)
      if (taskMap.has(root.id)) addTask(root)
    }

    return rows
  }, [tasks, collapsed])

  if (!tasks.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        No tasks yet. Add tasks using the button above.
      </div>
    )
  }

  return (
    <div className="rounded-lg border" style={{ overflowX: 'auto' }}>
      <Gantt
        tasks={ganttTasks}
        viewMode={viewMode}
        viewDate={viewDate}
        locale="en-GB"
        listCellWidth="220px"
        columnWidth={viewMode === ViewMode.Week ? 120 : 65}
        rowHeight={36}
        headerHeight={48}
        barFill={65}
        barCornerRadius={4}
        todayColor="rgba(99,102,241,0.15)"
        fontFamily="inherit"
        fontSize="12px"
        onClick={task => {
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
  )
}
