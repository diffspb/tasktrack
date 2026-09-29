import { Skeleton } from '@/components/ui/skeleton'
import { useTaskHistory, type AuditEvent } from './api'
import { Pill } from './ui'
import { fmtDateTime } from './format'

const ENTITY: Record<string, string> = {
  task: 'Task', comment: 'Comment', task_link: 'Relation', work_package: 'Assignment',
  work_package_draft: 'Assignment draft', result_proposal: 'Result', review: 'Review',
  task_session: 'Session', delivery: 'Delivery', recipient_acceptance: 'Recipient acceptance',
}

function short(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > 60 ? `${s.slice(0, 57)}…` : s
}

function Changes({ event }: { event: AuditEvent }) {
  const { before, after } = event
  if (event.action === 'updated' && before && after) {
    return (
      <ul className="mt-0.5 space-y-0.5">
        {Object.keys(after).filter(k => k !== 'version').map(k => (
          <li key={k} className="text-muted-foreground">
            <span className="font-mono">{k}</span>: {short(before[k])} → <span className="text-foreground">{short(after[k])}</span>
          </li>
        ))}
      </ul>
    )
  }
  const data = after ?? before
  if (!data) return null
  const highlights = ['title', 'content', 'verdict', 'rationale', 'version', 'note', 'reason', 'result', 'current_status_id']
    .filter(k => k in data)
  return highlights.length ? (
    <p className="mt-0.5 text-muted-foreground">
      {highlights.map(k => `${k}: ${short(data[k])}`).join(' · ')}
    </p>
  ) : null
}

/** Durable change history of a task from the audit log (ADR-018). */
export function TaskHistory({ taskId, nameOf }: { taskId: string; nameOf: (id: string) => string }) {
  const { data, isLoading } = useTaskHistory(taskId)
  if (isLoading) return <Skeleton className="h-20 w-full" />
  const items = [...(data?.items ?? [])].reverse()
  if (items.length === 0) return <p className="text-sm text-muted-foreground italic py-4 text-center">No history.</p>
  return (
    <ul className="space-y-2 text-xs" data-testid="task-history">
      {items.map(e => (
        <li key={e.id} className="border-l-2 pl-2.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-medium">{e.actor_id ? nameOf(e.actor_id) : 'system'}</span>
            <span className="text-muted-foreground">{e.action.replace(/_/g, ' ')}</span>
            <Pill tone="muted">{ENTITY[e.entity_type] ?? e.entity_type}</Pill>
            {e.session_id && <Pill tone="info">session</Pill>}
            <span className="text-muted-foreground ml-auto">{fmtDateTime(e.occurred_at)}</span>
          </div>
          {e.reason && <p className="italic text-muted-foreground">“{e.reason}”</p>}
          <Changes event={e} />
        </li>
      ))}
    </ul>
  )
}
