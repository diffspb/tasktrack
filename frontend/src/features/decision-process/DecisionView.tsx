import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  useDecision,
  useTaskSolutions,
  useProjectMembers,
  useCloseTask,
  type Task,
} from '@/features/tasks/api'
import { useState } from 'react'

interface Props {
  projectId: string
  task: Task
  isDecisionMaker: boolean
}

export function DecisionView({ projectId, task, isDecisionMaker }: Props) {
  const { data: decision } = useDecision(task.id)
  const { data: solutions = [] } = useTaskSolutions(task.id)
  const { data: members } = useProjectMembers(projectId)
  const close = useCloseTask(projectId, task.id)
  const [error, setError] = useState<string | null>(null)

  if (!decision) return null

  const accepted = solutions.filter(s => decision.accepted_solution_ids.includes(s.id))
  const userById = new Map(members?.items.map(m => [m.user.id, m.user]) ?? [])
  const dm = userById.get(decision.decision_maker_id)

  async function handleClose() {
    setError(null)
    try { await close.mutateAsync() }
    catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      setError(code ?? 'Close failed')
    }
  }

  return (
    <div className="space-y-2 rounded-lg border-2 border-green-200 bg-green-50/40 dark:border-green-900/40 dark:bg-green-900/10 p-3">
      <div className="flex items-center gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
          Decision
        </p>
        <span className="text-[10px] text-muted-foreground">
          by {dm?.display_name ?? '…'} · {new Date(decision.decided_at).toLocaleString()}
        </span>
      </div>

      {decision.note && (
        <p className="text-sm whitespace-pre-wrap">{decision.note}</p>
      )}

      <div className="space-y-1.5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Accepted ({accepted.length})
        </p>
        {accepted.map(s => {
          const a = task.assignments.find(x => x.id === s.assignment_id)
          const u = a ? userById.get(a.user_id) : null
          return (
            <div key={s.id} className="rounded-md border bg-background p-2">
              <div className="flex items-center gap-2 text-xs mb-1">
                <span className="font-medium">{u?.display_name ?? '…'}</span>
                <Badge variant="outline" className="text-[10px] capitalize h-5">{a?.role}</Badge>
              </div>
              <p className="text-sm whitespace-pre-wrap">{s.content}</p>
            </div>
          )
        })}
      </div>

      {task.global_status === 'decided' && isDecisionMaker && (
        <div className="flex items-center gap-2 pt-1">
          <Button size="sm" onClick={handleClose} disabled={close.isPending}>
            {close.isPending ? 'Closing…' : 'Close task'}
          </Button>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}
    </div>
  )
}
