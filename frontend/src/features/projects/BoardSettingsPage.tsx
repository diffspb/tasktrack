import { useParams } from 'react-router-dom'
import { BoardColumnEditor } from './BoardColumnEditor'

export function BoardSettingsPage() {
  const { id: projectId } = useParams<{ id: string }>()
  if (!projectId) return null

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-base font-semibold">Board columns</h2>
        <p className="text-sm text-muted-foreground">
          Map workflow statuses to board columns. Tasks appear in the column that contains their current status.
        </p>
      </div>
      <BoardColumnEditor projectId={projectId} />
    </div>
  )
}
