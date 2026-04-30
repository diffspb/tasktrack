import { useEffect, useState } from 'react'
import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  useAssignmentSolution,
  useCreateSolution,
  useUpdateSolution,
  useSubmitSolution,
  useWithdrawSolution,
  type Solution,
} from '@/features/tasks/api'

const STATUS_BADGE: Record<Solution['status'], { cls: string; label: string }> = {
  draft:              { cls: 'bg-muted text-muted-foreground',                                          label: 'Draft' },
  submitted:          { cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',        label: 'Submitted' },
  accepted:           { cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',    label: 'Accepted' },
  revision_requested: { cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', label: 'Revision requested' },
}

interface Props {
  projectId: string
  taskId: string
  assignmentId: string
  inFinalStatus: boolean
  taskClosed: boolean
}

export function SolutionEditor({ projectId, taskId, assignmentId, inFinalStatus, taskClosed }: Props) {
  const { data: solution, isLoading } = useAssignmentSolution(assignmentId)
  const create = useCreateSolution(projectId, taskId)
  const update = useUpdateSolution(projectId, taskId)
  const submit = useSubmitSolution(projectId, taskId)
  const withdraw = useWithdrawSolution(projectId, taskId)

  const [content, setContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [confirmingSubmit, setConfirmingSubmit] = useState(false)

  useEffect(() => {
    setContent(solution?.content ?? '')
  }, [solution?.id, solution?.content])

  if (isLoading) return null

  const editable =
    !solution || solution.status === 'draft' || solution.status === 'revision_requested'
  const dirty = (solution?.content ?? '') !== content
  const busy = create.isPending || update.isPending || submit.isPending || withdraw.isPending

  function handleError(err: unknown, fallback: string) {
    const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
    setError(code ?? fallback)
  }

  async function handleSave() {
    setError(null)
    try {
      if (!solution) {
        await create.mutateAsync({ assignmentId, content })
      } else {
        await update.mutateAsync({ solutionId: solution.id, content })
      }
    } catch (err) {
      handleError(err, 'Save failed')
    }
  }

  async function handleSubmit() {
    setError(null)
    setConfirmingSubmit(false)
    try {
      // Save pending edits first
      if (!solution) await create.mutateAsync({ assignmentId, content })
      else if (dirty) await update.mutateAsync({ solutionId: solution.id, content })
      const id = solution?.id ?? (await create.mutateAsync({ assignmentId, content })).id
      await submit.mutateAsync(id)
    } catch (err) {
      handleError(err, 'Submit failed')
    }
  }

  async function handleWithdraw() {
    if (!solution) return
    setError(null)
    try {
      await withdraw.mutateAsync(solution.id)
    } catch (err) {
      handleError(err, 'Withdraw failed')
    }
  }

  // Pre-condition messaging
  if (!inFinalStatus && !solution) {
    return (
      <div className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
        Move your assignment to the final status to draft a Solution.
      </div>
    )
  }
  if (taskClosed && solution?.status === 'accepted') {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">My Solution</p>
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${STATUS_BADGE[solution.status].cls}`}>
            {STATUS_BADGE[solution.status].label}
          </span>
        </div>
        <pre className="text-sm whitespace-pre-wrap rounded-md border bg-muted/30 p-3">
          {solution.content || <span className="text-muted-foreground">(empty)</span>}
        </pre>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">My Solution</p>
        {solution && (
          <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${STATUS_BADGE[solution.status].cls}`}>
            {STATUS_BADGE[solution.status].label}
          </span>
        )}
      </div>

      {solution?.status === 'revision_requested' && solution.revision_comment && (
        <div className="rounded-md border border-orange-200 bg-orange-50 dark:border-orange-900/40 dark:bg-orange-900/10 p-2.5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-orange-700 dark:text-orange-400 mb-1">
            Feedback
          </p>
          <p className="text-sm text-orange-900 dark:text-orange-100 whitespace-pre-wrap">{solution.revision_comment}</p>
        </div>
      )}

      <textarea
        value={content}
        onChange={e => setContent(e.target.value)}
        disabled={!editable || busy}
        placeholder="Describe your approach…"
        rows={5}
        className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring disabled:opacity-60"
      />

      {error && <p className="text-xs text-destructive">{error}</p>}

      <div className="flex flex-wrap gap-2">
        {editable && (
          <>
            {dirty && (
              <Button size="sm" variant="outline" onClick={handleSave} disabled={busy}>
                Save draft
              </Button>
            )}
            {!confirmingSubmit ? (
              <Button
                size="sm"
                onClick={() => setConfirmingSubmit(true)}
                disabled={busy || !content.trim()}
              >
                {solution?.status === 'revision_requested' ? 'Resubmit' : 'Submit Solution'}
              </Button>
            ) : (
              <div className="flex items-center gap-2 rounded-md border border-yellow-300 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 px-2 py-1">
                <span className="text-xs">Submit now? Decision-maker will be notified.</span>
                <Button size="sm" variant="ghost" onClick={() => setConfirmingSubmit(false)} disabled={busy}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSubmit} disabled={busy}>
                  Confirm
                </Button>
              </div>
            )}
          </>
        )}
        {solution?.status === 'submitted' && (
          <Button size="sm" variant="outline" onClick={handleWithdraw} disabled={busy}>
            Withdraw
          </Button>
        )}
        {solution?.status === 'accepted' && (
          <Badge variant="outline" className="text-[10px]">Accepted as Decision</Badge>
        )}
      </div>
    </div>
  )
}
