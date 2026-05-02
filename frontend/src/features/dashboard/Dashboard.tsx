import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useAuth } from '@/features/auth/AuthProvider'
import { useProjects } from '@/features/projects/api'
import type { Task } from '@/features/tasks/api'

function useMyTasks() {
  return useQuery<Task[]>({
    queryKey: ['my-tasks'],
    queryFn: () => api.get('/users/me/tasks').then(r => r.data),
  })
}

export function Dashboard() {
  const { user } = useAuth()
  const { data: projects = [] } = useProjects()
  const projectById = useMemo(
    () => new Map(projects.map(p => [p.id, p])),
    [projects],
  )

  const { data: tasks = [], isLoading } = useMyTasks()

  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  const active = tasks.filter(t => !t.deleted_at)
  const myAssigned = active.filter(t => t.assignee_id === user?.id)
  const myReported = active.filter(t => t.reporter_id === user?.id && t.assignee_id !== user?.id)

  const widgets = [
    { title: 'Assigned to me', tasks: myAssigned, emptyHint: 'No tasks assigned to you.', accent: 'blue' as const },
    { title: 'Reported by me', tasks: myReported, emptyHint: 'No tasks you reported.', accent: 'green' as const },
  ]

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-xl font-semibold">Welcome, {user?.display_name}</h1>
        <p className="text-sm text-muted-foreground">
          {active.length} task{active.length === 1 ? '' : 's'} touch you across all projects.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {widgets.map(w => (
          <DashboardCard
            key={w.title}
            title={w.title}
            tasks={w.tasks}
            emptyHint={w.emptyHint}
            projectById={projectById}
            accent={w.accent}
          />
        ))}
      </div>
    </div>
  )
}

function DashboardCard({
  title, tasks, emptyHint, projectById, accent,
}: {
  title: string
  tasks: Task[]
  emptyHint: string
  projectById: Map<string, { name: string; key: string }>
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
            const proj = projectById.get(t.project_id)
            return (
              <li key={t.id}>
                <button
                  onClick={() => navigate(`/tasks/${t.key}`)}
                  className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-muted/40 transition-colors"
                >
                  <span className="font-mono text-[10px] text-muted-foreground w-14 shrink-0">
                    {proj?.key ?? '…'}-{t.key.split('-')[1]}
                  </span>
                  <span className="text-sm flex-1 truncate">{t.title}</span>
                  <Badge variant="outline" className="text-[10px] capitalize h-4 shrink-0">{t.priority}</Badge>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
