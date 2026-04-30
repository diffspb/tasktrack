import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import {
  useTaskSolutions,
  useMakeDecision,
  useRequestRevision,
  type Task,
} from '@/features/tasks/api'

interface Props {
  projectId: string
  task: Task
}

export function DecisionPanel({ projectId, task }: Props) {
  const { data: solutions = [] } = useTaskSolutions(task.id)
  const make = useMakeDecision(projectId, task.id)
  const review = useRequestRevision(projectId, task.id)

  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [note, setNote] = useState('')
  const [feedback, setFeedback] = useState('')
  const [mode, setMode] = useState<null | 'decide' | 'revision'>(null)
  const [error, setError] = useState<string | null>(null)

  const submitted = solutions.filter(s => s.status === 'submitted')
  const busy = make.isPending || review.isPending

  function toggle(id: string) {
    const next = new Set(selected)
    if (next.has(id)) next.delete(id)
    else {
      if (!task.allow_multi_accept) next.clear()
      next.add(id)
    }
    setSelected(next)
  }

  function showError(err: unknown, fallback: string) {
    const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
    setError(code ?? fallback)
  }

  async function handleDecide() {
    setError(null)
    try {
      await make.mutateAsync({
        accepted_solution_ids: [...selected],
        note: note.trim() || undefined,
      })
      setMode(null)
      setSelected(new Set())
      setNote('')
    } catch (err) { showError(err, 'Decision failed') }
  }

  async function handleRevision() {
    setError(null)
    if (selected.size !== 1) {
      setError('Pick exactly one solution to send back')
      return
    }
    try {
      const [solId] = selected
      await review.mutateAsync({ solutionId: solId, feedback: feedback.trim() })
      setMode(null)
      setSelected(new Set())
      setFeedback('')
    } catch (err) { showError(err, 'Revision request failed') }
  }

  if (task.global_status !== 'awaiting_decision' && task.global_status !== 'in_revision') {
    return null
  }
  if (submitted.length === 0) {
    return (
      <div className="rounded-md border border-dashed p-3 text-xs text-muted-foreground">
        Waiting for leads to submit Solutions…
      </div>
    )
  }

  return (
    <div className="space-y-3 rounded-lg border-2 border-primary/30 bg-primary/[0.03] p-3">
      <div className="flex items-center gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-primary">Decision panel</p>
        {task.allow_multi_accept && (
          <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
            multi-accept
          </span>
        )}
      </div>

      <p className="text-xs text-muted-foreground">
        {task.allow_multi_accept
          ? 'Pick one or more solutions to accept. Or send a single one back for revision.'
          : 'Pick exactly one solution to accept. Or send a single one back for revision.'}
      </p>

      <div className="space-y-1.5">
        {submitted.map(s => (
          <label key={s.id} className="flex items-start gap-2 cursor-pointer rounded p-1.5 hover:bg-muted/50">
            <input
              type="checkbox"
              checked={selected.has(s.id)}
              onChange={() => toggle(s.id)}
              disabled={busy}
              className="mt-0.5"
            />
            <span className="text-sm flex-1 line-clamp-2">{s.content || <em className="text-muted-foreground">(empty)</em>}</span>
          </label>
        ))}
      </div>

      {mode === 'decide' && (
        <div className="space-y-2">
          <textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder="Note (optional) — why did you pick these?"
            rows={2}
            disabled={busy}
            className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
          />
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={() => setMode(null)} disabled={busy}>Cancel</Button>
            <Button size="sm" onClick={handleDecide} disabled={busy || selected.size === 0}>
              {busy ? 'Deciding…' : `Confirm — accept ${selected.size}`}
            </Button>
          </div>
        </div>
      )}

      {mode === 'revision' && (
        <div className="space-y-2">
          <textarea
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="Feedback for the assignee (required)"
            rows={3}
            disabled={busy}
            className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring"
          />
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={() => setMode(null)} disabled={busy}>Cancel</Button>
            <Button size="sm" onClick={handleRevision} disabled={busy || !feedback.trim() || selected.size !== 1}>
              {busy ? 'Sending…' : 'Send back for revision'}
            </Button>
          </div>
        </div>
      )}

      {!mode && (
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() => setMode('decide')}
            disabled={selected.size === 0 || (!task.allow_multi_accept && selected.size !== 1)}
          >
            Make Decision
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setMode('revision')}
            disabled={selected.size !== 1}
          >
            Request Revision
          </Button>
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
