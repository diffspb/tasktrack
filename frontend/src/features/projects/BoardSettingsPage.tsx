import { useParams } from 'react-router-dom'
import { useProjectByKey } from './api'
import { BoardColumnEditor } from './BoardColumnEditor'

export function BoardSettingsPage() {
  const { projectKey } = useParams<{ projectKey: string }>()
  const { data: projectData } = useProjectByKey(projectKey)
  const projectId = projectData?.id
  if (!projectId) return null

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-3">
      <h1 className="text-xl font-semibold">Board columns</h1>
      <p className="text-sm text-muted-foreground">
        Map workflow statuses to board columns. Tasks appear in the column that contains their current status.
      </p>
      <BoardColumnEditor projectId={projectId} />
    </div>
  )
}
