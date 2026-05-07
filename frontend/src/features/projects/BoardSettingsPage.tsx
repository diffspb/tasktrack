import { useParams } from 'react-router-dom'
import { useProjectByKey } from './api'
import { useProjectViews } from './viewsApi'
import { BoardColumnEditor } from './BoardColumnEditor'
import { Skeleton } from '@/components/ui/skeleton'

export function BoardSettingsPage() {
  const { projectKey } = useParams<{ projectKey: string }>()
  const { data: projectData } = useProjectByKey(projectKey)
  const projectId = projectData?.id
  const { data: views } = useProjectViews(projectId)

  if (!projectId || !views) {
    return <div className="max-w-3xl mx-auto p-6 space-y-3"><Skeleton className="h-64 w-full" /></div>
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-xl font-semibold">Board columns</h1>
      <p className="text-sm text-muted-foreground">
        Map workflow statuses to board columns for each kanban view.
      </p>
      {views.filter(v => v.type === 'kanban').map(v => (
        <div key={v.id} className="space-y-3">
          {views.filter(vv => vv.type === 'kanban').length > 1 && (
            <h2 className="text-sm font-semibold text-muted-foreground">{v.name}</h2>
          )}
          <BoardColumnEditor viewId={v.id} projectId={projectId} />
        </div>
      ))}
    </div>
  )
}
