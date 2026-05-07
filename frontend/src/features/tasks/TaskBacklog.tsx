import { useState, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useProjectByKey } from '@/features/projects/api'
import { Plus } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useAuth } from '@/features/auth/AuthProvider'
import {
  useProjectTasks, useProjectWorkflows, useProjectMembers, type Task,
} from './api'
import { TaskDetail } from './TaskDetail'
import { CreateTaskModal } from './CreateTaskModal'
import { TaskFilterBar, DEFAULT_FILTER, applyFilter, type FilterState } from './TaskFilter'
import { useProjectEvents, type TaskEvent } from './useProjectEvents'

export function TaskBacklog() {
  const { projectKey } = useParams<{ projectKey: string }>()
  const { data: projectData } = useProjectByKey(projectKey)
  const projectId = projectData?.id
  const { user } = useAuth()
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [filter, setFilter] = useState<FilterState>(DEFAULT_FILTER)
  const [flashIds, setFlashIds] = useState<Set<string>>(new Set())

  const qc = useQueryClient()
  useProjectEvents(projectId ?? null, (evt: TaskEvent) => {
    if (!projectId) return
    if (evt.type === 'task.created') {
      qc.invalidateQueries({ queryKey: ['tasks', projectId] })
    } else if (evt.type === 'task.updated' || evt.type === 'task.status_changed') {
      qc.setQueryData<Task[]>(['tasks', projectId], old => old?.map(t => t.id === evt.task_id ? evt.task! : t))
      qc.setQueryData(['task', evt.task_id], evt.task)
      if (evt.task?.key) qc.setQueryData(['task-by-key', evt.task.key], evt.task)
      setFlashIds(s => new Set(s).add(evt.task_id))
      setTimeout(() => setFlashIds(s => { const n = new Set(s); n.delete(evt.task_id); return n }), 2000)
    } else if (evt.type === 'task.deleted') {
      qc.setQueryData<Task[]>(['tasks', projectId], old => old?.filter(t => t.id !== evt.task_id))
    }
  })

  const { data: workflows } = useProjectWorkflows(projectId ?? '')
  const { data: tasks, isLoading } = useProjectTasks(projectId ?? '')

  const { data: members } = useProjectMembers(projectId ?? '')

  const defaultWorkflow = workflows?.find(w => w.is_default) ?? workflows?.[0]
  const statuses = defaultWorkflow?.statuses ?? []
  const transitions = defaultWorkflow?.transitions ?? []
  const statusById = useMemo(() => new Map(statuses.map(s => [s.id, s])), [statuses])
  const taskById = useMemo(() => new Map((tasks ?? []).map(t => [t.id, t])), [tasks])
  const userById = useMemo(
    () => new Map(members?.items.map(m => [m.user.id, m.user]) ?? []),
    [members],
  )

  const selectedTask = (tasks ?? []).find(t => t.id === selectedTaskId) ?? null

  const filtered = useMemo(
    () => applyFilter((tasks ?? []).filter(t => !t.deleted_at), filter, user?.id ?? ''),
    [tasks, filter, user?.id],
  )

  if (isLoading) {
    return (
      <div className="p-5 space-y-2">
        {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12 w-full" />)}
      </div>
    )
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left: list content */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Toolbar */}
        <div className="flex items-center gap-2 border-b px-5 py-3 shrink-0 flex-wrap">
          <TaskFilterBar filter={filter} onChange={setFilter} taskCount={filtered.length} />
          <div className="flex-1" />
          <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" /> Create task
          </Button>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center py-24 text-sm text-muted-foreground">
              No tasks match this filter.
            </div>
          ) : (
            <ul className="divide-y">
              {filtered.map(t => (
                <BacklogRow
                  key={t.id}
                  task={t}
                  statusName={statusById.get(t.current_status_id)?.name ?? '—'}
                  statusCategory={statusById.get(t.current_status_id)?.category}
                  assigneeName={t.assignee_id ? userById.get(t.assignee_id)?.display_name : undefined}
                  epicKey={t.parent_task_id ? taskById.get(t.parent_task_id)?.key : undefined}
                  isFlashing={flashIds.has(t.id)}
                  onClick={() => setSelectedTaskId(t.id)}
                />
              ))}
            </ul>
          )}
        </div>
      </div>{/* end left */}

      <TaskDetail
        task={selectedTask}
        statuses={statuses}
        transitions={transitions}
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

function BacklogRow({
  task, statusName, statusCategory, assigneeName, epicKey, isFlashing, onClick,
}: {
  task: Task
  statusName: string
  statusCategory?: 'initial' | 'intermediate' | 'final'
  assigneeName?: string
  epicKey?: string
  isFlashing?: boolean
  onClick: () => void
}) {
  const typeKey = task.task_type?.key ?? 'task'
  const statusCls =
    statusCategory === 'final' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
    statusCategory === 'initial' ? 'bg-muted text-muted-foreground' :
    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'

  return (
    <li>
      <div
        className={cn(
          'flex items-center gap-3 px-5 py-2.5 hover:bg-muted/40 transition-all duration-500 cursor-pointer',
          isFlashing && 'ring-2 ring-inset ring-primary/40 bg-primary/5',
        )}
        onClick={onClick}
      >
        <Link
          to={`/tasks/${task.key}`}
          onClick={e => e.stopPropagation()}
          className="font-mono text-xs font-semibold text-muted-foreground/70 hover:text-primary hover:underline w-20 shrink-0 transition-colors"
        >
          {task.key}
        </Link>
        <span className="text-xs text-muted-foreground/60 capitalize w-14 shrink-0">{typeKey}</span>
        <span className="flex-1 text-sm truncate">
          {epicKey && (
            <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 mr-1.5 shrink-0">
              {epicKey}
            </span>
          )}
          {task.title}
        </span>
        <Badge variant="outline" className="text-[10px] capitalize h-5 shrink-0">{task.priority}</Badge>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium shrink-0 ${statusCls}`}>{statusName}</span>
        {assigneeName && (
          <span className="text-[11px] text-muted-foreground/60 shrink-0 max-w-[80px] truncate">{assigneeName}</span>
        )}
      </div>
    </li>
  )
}
