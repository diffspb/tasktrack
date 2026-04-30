import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/AuthProvider'
import {
  useProjectTasks,
  useProjectWorkflows,
  useProjectResolutions,
  useProjectMembers,
  type Task,
  type GlobalStatus,
} from './api'
import { TaskDetail } from './TaskDetail'
import { CreateTaskModal } from './CreateTaskModal'

const GS_STYLES: Record<GlobalStatus, { cls: string; label: string }> = {
  open:              { cls: 'bg-muted text-muted-foreground',                                          label: 'Open' },
  in_progress:       { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',        label: 'In Progress' },
  awaiting_decision: { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300', label: 'Awaiting Decision' },
  in_revision:       { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', label: 'In Revision' },
  decided:           { cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',    label: 'Decided' },
  closed:            { cls: 'bg-muted text-muted-foreground',                                          label: 'Closed' },
}

type Filter = 'all' | 'mine' | 'awaiting_my_decision' | 'reported_by_me'

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'mine', label: 'My work' },
  { value: 'awaiting_my_decision', label: 'Awaiting my decision' },
  { value: 'reported_by_me', label: 'Reported by me' },
]

export function TaskBacklog() {
  const { id: projectId } = useParams<{ id: string }>()
  const { user } = useAuth()
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
  const userById = useMemo(
    () => new Map(members?.items.map(m => [m.user.id, m.user]) ?? []),
    [members],
  )

  const selectedTask = (tasks ?? []).find(t => t.id === selectedTaskId) ?? null

  const filtered = useMemo(() => {
    const list = tasks ?? []
    switch (filter) {
      case 'mine':
        return list.filter(t => t.assignments.some(a => a.user_id === user?.id))
      case 'awaiting_my_decision':
        return list.filter(t =>
          t.decision_maker_id === user?.id &&
          (t.global_status === 'awaiting_decision' || t.global_status === 'in_revision'),
        )
      case 'reported_by_me':
        return list.filter(t => t.reporter_id === user?.id)
      default:
        return list
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
        {defaultWorkflow && (
          <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" /> Create task
          </Button>
        )}
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
                userById={userById}
                onClick={() => setSelectedTaskId(t.id)}
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

      {defaultWorkflow && (
        <CreateTaskModal
          open={createOpen}
          projectId={projectId ?? ''}
          workflowId={defaultWorkflow.id}
          onClose={() => setCreateOpen(false)}
        />
      )}
    </div>
  )
}

function BacklogRow({
  task, userById, onClick,
}: {
  task: Task
  userById: Map<string, { display_name: string; email: string }>
  onClick: () => void
}) {
  const gs = GS_STYLES[task.global_status]
  return (
    <li>
      <button onClick={onClick} className="w-full flex items-center gap-3 px-5 py-2.5 hover:bg-muted/40 transition-colors text-left">
        <span className="font-mono text-xs font-semibold text-muted-foreground w-20 shrink-0">{task.key}</span>
        <span className="flex-1 text-sm truncate">{task.title}</span>
        <Badge variant="outline" className="text-[10px] capitalize h-5">{task.priority}</Badge>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium shrink-0 ${gs.cls}`}>{gs.label}</span>
        <div className="flex -space-x-1.5 w-16 shrink-0">
          {task.assignments.slice(0, 3).map(a => (
            <span
              key={a.id}
              title={userById.get(a.user_id)?.display_name ?? a.user_id}
              className="h-5 w-5 rounded-full bg-muted-foreground/20 border-2 border-background flex items-center justify-center text-[9px] font-bold"
            >
              {(userById.get(a.user_id)?.display_name ?? '??').slice(0, 2).toUpperCase()}
            </span>
          ))}
          {task.assignments.length > 3 && (
            <span className="h-5 w-5 rounded-full bg-muted border-2 border-background flex items-center justify-center text-[9px] text-muted-foreground">
              +{task.assignments.length - 3}
            </span>
          )}
        </div>
      </button>
    </li>
  )
}
