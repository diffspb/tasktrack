import { useParams, Navigate } from 'react-router-dom'
import { useAuth } from '@/features/auth/AuthProvider'
import { useProjectByKey } from './api'
import { useView, useProjectViews } from './viewsApi'
import { TaskBoard } from '@/features/tasks/TaskBoard'
import { TaskBacklog } from '@/features/tasks/TaskBacklog'
import { Skeleton } from '@/components/ui/skeleton'
import type { View } from './viewsApi'

interface ViewRedirectProps {
  type: View['type']
}

/** Redirects legacy /board and /backlog routes to the matching default view. */
export function ViewRedirect({ type }: ViewRedirectProps) {
  const { projectKey } = useParams<{ projectKey: string }>()
  const { data: project } = useProjectByKey(projectKey)
  const { data: views } = useProjectViews(project?.id)

  if (!project || !views) {
    return <div className="p-8"><Skeleton className="h-8 w-48" /></div>
  }

  const target = views.find(v => v.type === type && v.is_default) ?? views.find(v => v.type === type)
  if (!target) return <Navigate to="/projects" replace />
  return <Navigate to={`/projects/${projectKey}/views/${target.id}`} replace />
}

/** Renders the correct component based on view type. */
export function ViewPage() {
  const { viewId } = useParams<{ projectKey: string; viewId: string }>()
  const { data: view, isLoading } = useView(viewId)

  if (isLoading || !view) {
    return (
      <div className="p-8 space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (view.type === 'kanban') {
    return <TaskBoard viewId={view.id} projectId={view.project_id} />
  }
  if (view.type === 'backlog') {
    return <TaskBacklog viewId={view.id} projectId={view.project_id} />
  }

  return null
}
