import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useProjectByKey } from '@/features/projects/api'
import { useProjectMembers } from '@/features/tasks/api'
import { TaskTypeIcon } from '@/features/tasks/TaskTypeIcon'
import { useProjectControl } from './api'
import { WAITING_LABEL } from './format'
import { Pill, StateBadge } from './ui'

const REASON_TONE: Record<string, 'warning' | 'danger' | 'info' | 'muted'> = {
  no_work_package: 'warning', work_package_changed: 'warning', no_assignee: 'warning',
  blocked: 'danger', session_stale: 'danger', awaiting_review: 'info', changes_requested: 'warning',
  awaiting_recipient: 'info', unverified_result: 'muted',
  impact_pending: 'warning', blocker_registered: 'danger', not_ready: 'warning',
}

/** Manager's view of open work and why it waits (FR-003 TT-22). */
export function ControlPage() {
  const { projectKey } = useParams<{ projectKey: string }>()
  const { data: project } = useProjectByKey(projectKey)
  const { data: members } = useProjectMembers(project?.id)
  const [reason, setReason] = useState<string>()
  const [specialization, setSpecialization] = useState<string>()
  const { data, isLoading } = useProjectControl(project?.id, { reason, specialization })
  const nameOf = (id: string | null) =>
    id ? members?.items.find(m => m.user.id === id)?.user.display_name ?? id.slice(0, 8) : '—'

  const chip = (active: boolean) => cn(
    'rounded-full border px-2.5 py-0.5 text-xs transition-colors',
    active ? 'border-primary bg-primary/10 text-primary' : 'hover:bg-muted',
  )

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Control</h1>
        <p className="text-sm text-muted-foreground">
          Open work and why it waits: missing assignment, review queue, silent sessions, blocked tasks.
        </p>
      </div>

      {isLoading || !data ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <>
          <div className="space-y-2">
            <div className="flex flex-wrap gap-1.5" data-testid="reason-filters">
              <button className={chip(!reason)} onClick={() => setReason(undefined)}>
                All open · {data.summary.open_tasks}
              </button>
              {Object.entries(data.summary.by_reason).map(([r, n]) => (
                <button key={r} className={chip(reason === r)} onClick={() => setReason(reason === r ? undefined : r)}>
                  {WAITING_LABEL[r] ?? r} · {n}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(data.summary.by_specialization).map(([s, n]) => (
                <button key={s} className={chip(specialization === s)}
                  onClick={() => setSpecialization(specialization === s || s === '—' ? undefined : s)}>
                  {s} · {n}
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-lg border overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/40 text-xs text-muted-foreground">
                <tr>
                  <th className="text-left font-medium px-3 py-2">Task</th>
                  <th className="text-left font-medium px-3 py-2">Status</th>
                  <th className="text-left font-medium px-3 py-2">Assignee</th>
                  <th className="text-left font-medium px-3 py-2">Specialization</th>
                  <th className="text-left font-medium px-3 py-2">Result</th>
                  <th className="text-left font-medium px-3 py-2">Waiting on</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.items.map(i => (
                  <tr key={i.id}>
                    <td className="px-3 py-2">
                      <Link to={`/tasks/${i.key}`} className="flex items-center gap-2 hover:underline">
                        <TaskTypeIcon typeKey={i.task_type ?? 'task'} size={13} />
                        <span className="font-mono text-xs text-muted-foreground">{i.key}</span>
                        <span className="truncate max-w-72">{i.title}</span>
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-xs">{i.status}</td>
                    <td className="px-3 py-2 text-xs">{nameOf(i.assignee_id)}</td>
                    <td className="px-3 py-2 text-xs">{i.specialization ?? '—'}</td>
                    <td className="px-3 py-2"><StateBadge state={i.result_state} /></td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {i.waiting.map(w => (
                          <Pill key={w} tone={REASON_TONE[w] ?? 'muted'}>
                            {WAITING_LABEL[w] ?? w}
                            {w === 'blocked' && i.blocked_by.length > 0 && `: ${i.blocked_by.join(', ')}`}
                            {w === 'session_stale' && i.active_session && ` ${i.active_session.silent_hours} h`}
                          </Pill>
                        ))}
                        {i.waiting.length === 0 && <span className="text-xs text-muted-foreground">in progress</span>}
                      </div>
                    </td>
                  </tr>
                ))}
                {data.items.length === 0 && (
                  <tr><td colSpan={6} className="px-3 py-6 text-center text-sm text-muted-foreground">Nothing here.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
