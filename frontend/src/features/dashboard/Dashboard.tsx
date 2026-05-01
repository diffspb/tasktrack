import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/features/auth/AuthProvider'
import { useProjects } from '@/features/projects/api'
import type { Task, GlobalStatus } from '@/features/tasks/api'

const GS_STYLES: Record<GlobalStatus, { cls: string; label: string }> = {
  open:              { cls: 'bg-muted text-muted-foreground',                                          label: 'Open' },
  in_progress:       { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',        label: 'In Progress' },
  awaiting_decision: { cls: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300', label: 'Awaiting Decision' },
  in_revision:       { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', label: 'In Revision' },
  decided:           { cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',    label: 'Decided' },
  closed:            { cls: 'bg-muted text-muted-foreground',                                          label: 'Closed' },
}

function useMyTasks(role?: 'assignee' | 'reporter' | 'dm', global_status?: GlobalStatus) {
  const params = new URLSearchParams()
  if (role) params.set('role', role)
  if (global_status) params.set('global_status', global_status)
  const qs = params.toString()
  return useQuery<Task[]>({
    queryKey: ['my-tasks', role ?? 'all', global_status ?? 'all'],
    queryFn: () => api.get(`/users/me/tasks${qs ? '?' + qs : ''}`).then(r => r.data),
  })
}

export function Dashboard() {
  const { user } = useAuth()
  const { data: projects = [] } = useProjects()
  const projectByid = useMemo(
    () => new Map(projects.map(p => [p.id, p])),
    [projects],
  )

  const all = useMyTasks()
  const awaiting = useMyTasks('dm', 'awaiting_decision')
  const inRevision = useMyTasks('dm', 'in_revision')
  const myAssigned = useMyTasks('assignee')

  if (all.isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  // Compute "Needs my work": tasks where I have an assignment AND there's
  // a Solution in revision_requested for me. We can derive part of this
  // from the assignment list — those whose task is in_revision and I have
  // an assignment.
  const needsMyWork = (myAssigned.data ?? []).filter(
    t => t.global_status === 'in_revision' &&
         t.assignments.some(a => a.user_id === user?.id),
  )

  const widgets = [
    { title: 'Awaiting my decision', tasks: awaiting.data ?? [], emptyHint: 'No tasks waiting on you.', accent: 'yellow' as const },
    { title: 'Needs my work',        tasks: needsMyWork,         emptyHint: 'Nothing to redo right now.', accent: 'orange' as const },
    { title: 'In revision (DM)',     tasks: inRevision.data ?? [], emptyHint: '', accent: 'orange' as const },
    { title: 'My active tasks',      tasks: (myAssigned.data ?? []).filter(t => t.global_status !== 'closed' && t.global_status !== 'decided'), emptyHint: 'No active assignments.', accent: 'blue' as const },
  ]

  const visible = widgets.filter(w => w.tasks.length > 0 || (w.title === 'Awaiting my decision' || w.title === 'My active tasks'))

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-xl font-semibold">Welcome, {user?.display_name}</h1>
        <p className="text-sm text-muted-foreground">{(all.data ?? []).length} task{(all.data ?? []).length === 1 ? '' : 's'} touch you across all projects.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {visible.map(w => (
          <DashboardCard key={w.title} title={w.title} tasks={w.tasks} emptyHint={w.emptyHint} projectByid={projectByid} accent={w.accent} />
        ))}
      </div>
    </div>
  )
}

function DashboardCard({
  title, tasks, emptyHint, projectByid, accent,
}: {
  title: string
  tasks: Task[]
  emptyHint: string
  projectByid: Map<string, { name: string; key: string }>
  accent: 'yellow' | 'orange' | 'blue' | 'green'
}) {
  const navigate = useNavigate()
  const accentCls = {
    yellow: 'border-yellow-200 dark:border-yellow-900/40',
    orange: 'border-orange-200 dark:border-orange-900/40',
    blue:   'border-blue-200 dark:border-blue-900/40',
    green:  'border-green-200 dark:border-green-900/40',
  }[accent]

  return (
    <section className={`rounded-lg border-2 ${accentCls} bg-background overflow-hidden`}>
      <header className="flex items-baseline justify-between border-b px-4 py-2.5">
        <h2 className="text-sm font-semibold">{title}</h2>
        <span className="text-xs text-muted-foreground">{tasks.length}</span>
      </header>
      {tasks.length === 0 ? (
        <p className="px-4 py-6 text-center text-xs text-muted-foreground">{emptyHint}</p>
      ) : (
        <ul className="divide-y max-h-64 overflow-y-auto">
          {tasks.map(t => {
            const proj = projectByid.get(t.project_id)
            const gs = GS_STYLES[t.global_status]
            return (
              <li key={t.id}>
                <button
                  onClick={() => navigate(`/projects/${t.project_id}/backlog`)}
                  className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-muted/40 transition-colors"
                >
                  <span className="font-mono text-[10px] text-muted-foreground w-14 shrink-0">
                    {proj?.key}
                  </span>
                  <span className="text-sm flex-1 truncate">{t.title}</span>
                  <Badge variant="outline" className="text-[10px] capitalize h-4 shrink-0">{t.priority}</Badge>
                  <span className={`rounded px-1.5 py-0.5 text-[9px] font-medium shrink-0 ${gs.cls}`}>
                    {gs.label}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
