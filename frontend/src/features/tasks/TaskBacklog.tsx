import { useState, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Plus, ExternalLink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/AuthProvider'
import {
  useProjectTasks, useProjectWorkflows, useProjectResolutions, useProjectMembers, type Task,
} from './api'
import { TaskDetail } from './TaskDetail'
import { CreateTaskModal } from './CreateTaskModal'

type Filter = 'all' | 'mine' | 'reported_by_me'

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'mine', label: 'My work' },
  { value: 'reported_by_me', label: 'Reported by me' },
]

export function TaskBacklog() {
  const { id: projectId } = useParams<{ id: string }>()
  const { user } = useAuth()
  const navigate = useNavigate()
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [filter, setFilter] = useState<Filter>('all')

  const { data: workflows } = useProjectWorkflows(projectId ?? '')
  const { data: tasks, isLoading } = useProjectTasks(projectId ?? '')
  const { data: resolutions = [] } = useProjectResolutions(projectId ?? '')
  const { data: members } = useProjectMembers(projectId ?? '')

  const defaultWorkflow = workflows?.find(w => w.is_default) ?? workflows?.[0]
  const statuses = defaultWorkflow?.statuses ?? []
  const transitions = defaultWorkflow?.transitions ?? []
  const statusById = useMemo(
    () => new Map(statuses.map(s => [s.id, s])),
    [statuses],
  )
  const userById = useMemo(
    () => new Map(members?.items.map(m => [m.user.id, m.user]) ?? []),
    [members],
  )

  const selectedTask = (tasks ?? []).find(t => t.id === selectedTaskId) ?? null

  const filtered = useMemo(() => {
    const list = (tasks ?? []).filter(t => !t.deleted_at)
    switch (filter) {
      case 'mine': return list.filter(t => t.assignee_id === user?.id)
      case 'reported_by_me': return list.filter(t => t.reporter_id === user?.id)
      default: return list
    }
  }, [tasks, filter, user?.id])

  if (isLoading) {
    return (
      <div className="p-5 space-y-2">
        {[1, 2, 3, 4, 5].map(i => <Skeleton key={i} className="h-12 w-full" />)}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b px-5 py-3 shrink-0 flex-wrap">
        <div className="flex items-center gap-1">
          {FILTERS.map(f => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
                filter === f.value
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-muted'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <span className="text-xs text-muted-foreground">{filtered.length} tasks</span>
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
                onClick={() => setSelectedTaskId(t.id)}
                onOpenPage={() => navigate(`/tasks/${t.key}`)}
              />
            ))}
          </ul>
        )}
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

function BacklogRow({
  task, statusName, statusCategory, assigneeName, onClick, onOpenPage,
}: {
  task: Task
  statusName: string
  statusCategory?: 'initial' | 'intermediate' | 'final'
  assigneeName?: string
  onClick: () => void
  onOpenPage: () => void
}) {
  const typeKey = task.task_type?.key ?? 'task'
  const statusCls =
    statusCategory === 'final' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
    statusCategory === 'initial' ? 'bg-muted text-muted-foreground' :
    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'

  return (
    <li className="group">
      <div className="flex items-center gap-3 px-5 py-2.5 hover:bg-muted/40 transition-colors">
        <button onClick={onClick} className="flex items-center gap-3 flex-1 text-left min-w-0">
          <span className="font-mono text-xs font-semibold text-muted-foreground w-20 shrink-0">{task.key}</span>
          <span className="text-xs text-muted-foreground/60 capitalize w-14 shrink-0">{typeKey}</span>
          <span className="flex-1 text-sm truncate">{task.title}</span>
          <Badge variant="outline" className="text-[10px] capitalize h-5 shrink-0">{task.priority}</Badge>
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium shrink-0 ${statusCls}`}>{statusName}</span>
          {assigneeName && (
            <span className="text-[11px] text-muted-foreground/60 shrink-0 max-w-[80px] truncate">{assigneeName}</span>
          )}
        </button>
        <button
          onClick={onOpenPage}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground/50 hover:text-muted-foreground p-1 rounded"
          title="Open task page"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </button>
      </div>
    </li>
  )
}
