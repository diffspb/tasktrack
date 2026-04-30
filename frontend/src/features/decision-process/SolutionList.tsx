import { useTaskSolutions, useProjectMembers, type Solution, type Assignment } from '@/features/tasks/api'
import { Badge } from '@/components/ui/badge'

const STATUS_BADGE: Record<Solution['status'], { cls: string; label: string }> = {
  draft:              { cls: 'bg-muted text-muted-foreground',                                          label: 'Draft' },
  submitted:          { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',        label: 'Submitted' },
  accepted:           { cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',    label: 'Accepted' },
  revision_requested: { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', label: 'Revision' },
}

interface Props {
  projectId: string
  taskId: string
  assignments: Assignment[]
  currentUserId: string
}

export function SolutionList({ projectId, taskId, assignments, currentUserId }: Props) {
  const { data: solutions = [], isLoading, isError } = useTaskSolutions(taskId)
  const { data: members } = useProjectMembers(projectId)

  if (isLoading) return null
  if (isError) {
    return (
      <p className="text-xs text-muted-foreground italic">
        Solutions are visible after a Decision is made.
      </p>
    )
  }
  if (solutions.length === 0) {
    return (
      <p className="text-xs text-muted-foreground italic">No solutions submitted yet.</p>
    )
  }

  const userById = new Map(members?.items.map(m => [m.user.id, m.user]) ?? [])

  return (
    <div className="space-y-2">
      {solutions.map(s => {
        const a = assignments.find(x => x.id === s.assignment_id)
        const u = a ? userById.get(a.user_id) : null
        const isMine = a?.user_id === currentUserId
        return (
          <div key={s.id} className="rounded-md border bg-muted/20 p-2.5 space-y-1.5">
            <div className="flex items-center gap-2 text-xs">
              <span className="font-medium">
                {isMine ? 'You' : u?.display_name ?? '…'}
              </span>
              <Badge variant="outline" className="text-[10px] capitalize h-5">{a?.role}</Badge>
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${STATUS_BADGE[s.status].cls}`}>
                {STATUS_BADGE[s.status].label}
              </span>
              <div className="flex-1" />
              {s.submitted_at && (
                <span className="text-[10px] text-muted-foreground">
                  {new Date(s.submitted_at).toLocaleString()}
                </span>
              )}
            </div>
            <p className="text-sm whitespace-pre-wrap">{s.content || <span className="text-muted-foreground italic">(empty)</span>}</p>
            {s.status === 'revision_requested' && s.revision_comment && (
              <div className="rounded border border-orange-200 bg-orange-50 dark:border-orange-900/40 dark:bg-orange-900/10 px-2 py-1.5">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-orange-700 dark:text-orange-400">
                  Feedback
                </p>
                <p className="text-xs text-orange-900 dark:text-orange-100 whitespace-pre-wrap">{s.revision_comment}</p>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
