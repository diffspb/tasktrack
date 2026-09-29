import { useState } from 'react'
import { Button } from '@/components/ui/button'
import type { Task } from '@/features/tasks/api'
import { useClaimTask, useSessionAction, useSessions } from './api'
import { SectionLabel, StateBadge } from './ui'
import { fmtDateTime, inputCls } from './format'

interface Props {
  task: Task
  currentUserId: string
  isManager: boolean
  nameOf: (id: string) => string
}

/**
 * Work sessions (ADR-022, TT-12): who works on the task, where, since when, last
 * checkpoint. A session ends only explicitly — never by timeout.
 */
export function SessionPanel({ task, currentUserId, isManager, nameOf }: Props) {
  const { data: sessions = [] } = useSessions(task.id)
  const claim = useClaimTask(task.id)
  const act = useSessionAction(task.id)
  const [note, setNote] = useState('')
  const [reason, setReason] = useState('')
  const [releasing, setReleasing] = useState(false)

  const active = sessions.find(s => s.state === 'active' && s.role === 'executor')
  const past = sessions.filter(s => s !== active)
  const isOwner = active?.user_id === currentUserId
  const canClaim = !active && task.assignee_id === currentUserId

  if (!active && !canClaim && past.length === 0) return null

  return (
    <div className="space-y-2" data-testid="session-panel">
      <SectionLabel>Work session</SectionLabel>
      {active ? (
        <div className="rounded-lg border p-3 space-y-2 text-sm">
          <div className="flex items-center gap-2 text-xs">
            <StateBadge state="active" />
            <span>{isOwner ? 'You' : nameOf(active.user_id)}</span>
            {active.machine && <span className="text-muted-foreground">on {active.machine}</span>}
          </div>
          <p className="text-xs text-muted-foreground">
            Started {fmtDateTime(active.created_at)}
            {active.last_checkpoint_at ? ` · last checkpoint ${fmtDateTime(active.last_checkpoint_at)}` : ' · no checkpoints yet'}
          </p>
          {active.checkpoints.length > 0 && (
            <ul className="text-xs space-y-0.5 max-h-32 overflow-y-auto">
              {active.checkpoints.map(c => (
                <li key={c.id}><span className="text-muted-foreground">{fmtDateTime(c.created_at)}</span> — {c.note}</li>
              ))}
            </ul>
          )}
          {isOwner && (
            <div className="flex gap-1.5">
              <input aria-label="Checkpoint note" className={inputCls} placeholder="Checkpoint note" value={note}
                onChange={e => setNote(e.target.value)} />
              <Button size="sm" variant="outline" disabled={!note.trim()}
                onClick={() => act.mutate({ sessionId: active.id, action: 'checkpoints', body: { note } }, { onSuccess: () => setNote('') })}>
                Checkpoint
              </Button>
              <Button size="sm" onClick={() => act.mutate({ sessionId: active.id, action: 'complete', body: {} })}>Complete</Button>
            </div>
          )}
          {(isOwner || isManager) && (releasing ? (
            <div className="flex gap-1.5">
              <input aria-label="Release reason" className={inputCls}
                placeholder="Why it is safe to release (e.g. process verified stopped)" value={reason}
                onChange={e => setReason(e.target.value)} />
              <Button size="sm" variant="destructive" disabled={!reason.trim()}
                onClick={() => act.mutate({ sessionId: active.id, action: 'release', body: { reason } })}>
                Release
              </Button>
            </div>
          ) : (
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={() => setReleasing(true)}>
              Release session…
            </Button>
          ))}
        </div>
      ) : canClaim && (
        <Button size="sm" variant="outline" disabled={claim.isPending}
          onClick={() => claim.mutate({ client: 'web' })}>
          Start work session
        </Button>
      )}
      {past.length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">Previous sessions ({past.length})</summary>
          <ul className="mt-1 space-y-0.5">
            {past.map(s => (
              <li key={s.id}>
                <StateBadge state={s.state} /> {nameOf(s.user_id)} · {fmtDateTime(s.created_at)}
                {s.end_reason ? ` — ${s.end_reason}` : ''}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
