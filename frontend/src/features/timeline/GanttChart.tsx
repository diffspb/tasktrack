import { useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { Gantt, ViewMode } from 'gantt-task-react'
import type { Task as GanttTask } from 'gantt-task-react'
import 'gantt-task-react/dist/index.css'
import { cn } from '@/lib/utils'
import { TaskTypeIcon } from '@/features/tasks/TaskTypeIcon'
import type { Task } from '@/features/tasks/api'

const TYPE_COLORS: Record<string, string> = {
  bug:      '#ef4444',
  story:    '#10b981',
  epic:     '#f59e0b',
  decision: '#8b5cf6',
  task:     '#6366f1',
}

const LIST_MIN = 180
const LIST_MAX = 600
const LIST_DEFAULT = 320

function addDays(d: Date, n: number): Date {
  return new Date(d.getTime() + n * 86_400_000)
}
function toDate(s: string): Date {
  const d = new Date(s)
  d.setHours(0, 0, 0, 0)
  return d
}
function resolveStart(task: Task): Date {
  return toDate(task.start_date ?? task.created_at)
}
function resolveEnd(task: Task, allTasks: Task[]): Date {
  const start = resolveStart(task)
  if (task.duration_days) return addDays(start, task.duration_days)
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

/** Estimate number of time periods (months or weeks) in the task date range. */
function countPeriods(tasks: GanttTask[], mode: ViewMode): number {
  if (!tasks.length) return 6
  const minMs = Math.min(...tasks.map(t => t.start.getTime()))
  const maxMs = Math.max(...tasks.map(t => t.end.getTime()))
  const min = new Date(minMs)
  const max = new Date(maxMs)
  if (mode === ViewMode.Month) {
    return Math.max(1, (max.getFullYear() - min.getFullYear()) * 12 + max.getMonth() - min.getMonth() + 1)
  }
  return Math.max(1, Math.ceil((maxMs - minMs) / (7 * 86_400_000)) + 1)
}

// ── Task metadata ─────────────────────────────────────────────────────────────

type TaskMeta = Map<string, { depth: number; realTask: Task }>

// ── Custom list components (stable refs, fresh data via useRef) ───────────────

type ListHeaderProps = { headerHeight: number; rowWidth: string; fontFamily: string; fontSize: string }
type ListTableProps = {
  rowHeight: number; rowWidth: string; fontFamily: string; fontSize: string; locale: string
  tasks: GanttTask[]; selectedTaskId: string
  setSelectedTask: (id: string) => void
  onExpanderClick: (t: GanttTask) => void
}

function makeListComponents(
  dataRef: React.RefObject<{ taskMeta: TaskMeta; selectedTaskId: string | null; onTaskSelect?: (t: Task) => void }>,
) {
  const Header = function GanttListHeader({ headerHeight, rowWidth }: ListHeaderProps) {
    return (
      <div
        style={{ height: headerHeight, width: rowWidth, minWidth: rowWidth }}
        className="flex items-end px-3 pb-2 bg-muted/30 border-b shrink-0"
      >
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Task</span>
      </div>
    )
  }

  const Table = function GanttListTable({ rowHeight, rowWidth, tasks: visible, onExpanderClick }: ListTableProps) {
    const { taskMeta, selectedTaskId, onTaskSelect } = dataRef.current!
    return (
      <div style={{ width: rowWidth, minWidth: rowWidth }}>
        {visible.map(gt => {
          const meta     = taskMeta.get(gt.id)
          const realTask = meta?.realTask
          const depth    = meta?.depth ?? 0
          const isGroup  = gt.type === 'project'
          const isSelected = gt.id === selectedTaskId

          return (
            <div
              key={gt.id}
              style={{ height: rowHeight }}
              className={cn(
                'flex items-center px-2 border-b gap-1 cursor-pointer select-none overflow-hidden',
                isSelected ? 'bg-primary/5' : 'hover:bg-muted/30',
              )}
              onClick={() => realTask && onTaskSelect?.(realTask)}
            >
              <div style={{ width: depth * 14, flexShrink: 0 }} />

              <div className="w-5 h-full shrink-0 flex items-center justify-center">
                {isGroup ? (
                  <button
                    className="rounded p-0.5 text-muted-foreground hover:text-foreground"
                    onClick={e => { e.stopPropagation(); onExpanderClick(gt) }}
                  >
                    {gt.hideChildren
                      ? <ChevronRight className="h-3.5 w-3.5" />
                      : <ChevronDown  className="h-3.5 w-3.5" />}
                  </button>
                ) : null}
              </div>

              <div className="w-4 shrink-0 flex items-center justify-center">
                {realTask && (
                  <TaskTypeIcon
                    typeKey={realTask.task_type?.key ?? 'task'}
                    color={realTask.task_type?.color ?? '#6366f1'}
                    size={12}
                  />
                )}
              </div>

              {realTask && (
                <Link
                  to={`/tasks/${realTask.key}`}
                  onClick={e => e.stopPropagation()}
                  className="font-mono text-[10px] font-semibold text-muted-foreground hover:text-primary shrink-0"
                >
                  {realTask.key}
                </Link>
              )}

              <span className="text-xs truncate ml-0.5 text-foreground/90">{gt.name}</span>
            </div>
          )
        })}
      </div>
    )
  }

  return { Header, Table }
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  tasks: Task[]
  viewMode: ViewMode
  viewDate?: Date
  onTaskSelect?: (task: Task) => void
  selectedTaskId?: string | null
  /** Width of the chart area measured by the parent (avoids ResizeObserver measuring inside overflow:hidden) */
  containerWidth?: number
}

export function GanttChart({ tasks, viewMode, viewDate, onTaskSelect, selectedTaskId, containerWidth }: Props) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [listWidth, setListWidth] = useState(LIST_DEFAULT)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const isDragging = useRef(false)

  // containerWidth is measured by the parent on the flex row that contains this chart.
  // Subtract p-4 padding (32px) that wraps the GanttChart inside GanttPage.
  const wrapperWidth = containerWidth ? containerWidth - 32 : 0

  // Drag-to-resize list panel
  function startDrag(e: React.MouseEvent) {
    e.preventDefault()
    isDragging.current = true
    const startX = e.clientX
    const startW = listWidth
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    function onMove(ev: MouseEvent) {
      if (!isDragging.current) return
      setListWidth(Math.max(LIST_MIN, Math.min(LIST_MAX, startW + ev.clientX - startX)))
    }
    function onUp() {
      isDragging.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  // Build ganttTasks + taskMeta
  const { ganttTasks, taskMeta } = useMemo<{ ganttTasks: GanttTask[]; taskMeta: TaskMeta }>(() => {
    const ganttTasks: GanttTask[] = []
    const taskMeta: TaskMeta = new Map()
    const roots   = tasks.filter(t => !tasks.some(p => p.id === t.parent_task_id))
    const taskMap = new Map(tasks.map(t => [t.id, t]))

    function addTask(task: Task, parentId: string | undefined, depth: number) {
      const start    = resolveStart(task)
      const end      = resolveEnd(task, tasks)
      const color    = TYPE_COLORS[task.task_type?.key ?? 'task'] ?? '#6366f1'
      const children = tasks.filter(t => t.parent_task_id === task.id)
      const isGroup  = children.length > 0
      taskMeta.set(task.id, { depth, realTask: task })
      ganttTasks.push({
        id: task.id, name: task.title,
        type: isGroup ? 'project' : 'task',
        project: parentId, start,
        end: end <= start ? addDays(start, 1) : end,
        progress: 0,
        hideChildren: collapsed.has(task.id),
        styles: isGroup
          ? { backgroundColor: color + '22', progressColor: color, backgroundSelectedColor: color + '44' }
          : { backgroundColor: color + 'bb', progressColor: color, backgroundSelectedColor: color },
      })
      if (!collapsed.has(task.id)) {
        for (const child of children) addTask(child, task.id, depth + 1)
      }
    }
    for (const root of roots) {
      if (taskMap.has(root.id)) addTask(root, undefined, 0)
    }
    return { ganttTasks, taskMeta }
  }, [tasks, collapsed])

  // Dynamic column width: fill the available chart area
  const columnWidth = useMemo(() => {
    // 16px = gantt-task-react VerticalScroll flex item (1rem, flex-shrink:0)
    // +6 padding columns instead of +4 to buffer library's own preStepsCount
    const chartArea = wrapperWidth - listWidth - 16
    if (chartArea <= 0) return viewMode === ViewMode.Week ? 120 : 65
    const periods = countPeriods(ganttTasks, viewMode) + 6
    const minCol  = viewMode === ViewMode.Week ? 60 : 45
    return Math.max(minCol, Math.floor(chartArea / periods))
  }, [wrapperWidth, listWidth, ganttTasks, viewMode])

  // Stable list components (data via ref)
  const dataRef = useRef({ taskMeta, selectedTaskId: selectedTaskId ?? null, onTaskSelect })
  dataRef.current = { taskMeta, selectedTaskId: selectedTaskId ?? null, onTaskSelect }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const { Header: CustomListHeader, Table: CustomListTable } = useMemo(() => makeListComponents(dataRef), [])

  if (!tasks.length) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
        No tasks yet. Add tasks using the button above.
      </div>
    )
  }

  return (
    <div ref={wrapperRef} className="rounded-lg border overflow-hidden relative">
      <Gantt
        tasks={ganttTasks}
        viewMode={viewMode}
        viewDate={viewDate}
        locale="en-GB"
        listCellWidth={`${listWidth}px`}
        columnWidth={columnWidth}
        rowHeight={36}
        headerHeight={48}
        barFill={65}
        barCornerRadius={4}
        todayColor="rgba(99,102,241,0.15)"
        fontFamily="inherit"
        fontSize="12px"
        TaskListHeader={CustomListHeader}
        TaskListTable={CustomListTable}
        onExpanderClick={task => {
          setCollapsed(prev => {
            const next = new Set(prev)
            if (next.has(task.id)) next.delete(task.id)
            else next.add(task.id)
            return next
          })
        }}
      />

      {/* Drag handle — sits at the list/chart boundary */}
      <div
        style={{ position: 'absolute', left: listWidth - 3, top: 0, bottom: 0, width: 6, zIndex: 20 }}
        className="cursor-col-resize group flex items-stretch"
        onMouseDown={startDrag}
      >
        <div className="w-0.5 mx-auto bg-border group-hover:bg-primary/50 transition-colors" />
      </div>
    </div>
  )
}
