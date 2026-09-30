import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { useTransitionStatus, type Status, type Task, type Transition } from '../api'
import { SectionLabel } from './ui'

const ERRORS: Record<string, (missing?: string[]) => string> = {
  TASK_BLOCKED_BY_SUBTASKS: () => 'Blocked: every subtask needs a submitted result first.',
  RESULT_NOT_REVIEWED: () => 'This task type closes only after its result is reviewed.',
  TRANSITION_FIELDS_REQUIRED: missing => `Fill in first: ${missing?.join(', ') ?? ''}.`,
}

interface Props {
  task: Task
  statuses: Status[]
  transitions: Transition[]
  mode: 'page' | 'panel'
}

/** "Move to" buttons of the task's workflow; backward moves ask for confirmation. */
export function StatusActions({ task, statuses, transitions, mode }: Props) {
  const transition = useTransitionStatus(task.project_id)
  const [confirming, setConfirming] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const currentStatus = statuses.find(s => s.id === task.current_status_id)
  const nextStatuses = transitions
    .filter(t => t.from_status_id === task.current_status_id)
    .map(t => statuses.find(s => s.id === t.to_status_id))
    .filter((s): s is Status => !!s)

  const isBackward = (toStatusId: string) => {
    const target = statuses.find(s => s.id === toStatusId)
    return !!currentStatus && !!target && target.position < currentStatus.position
  }

  async function perform(statusId: string) {
    setError(null); setConfirming(null)
    try {
      await transition.mutateAsync({ taskId: task.id, status_id: statusId })
    } catch (err) {
      const detail = (err as AxiosError<{ detail: { code: string; missing?: string[] } }>)?.response?.data?.detail
      setError((detail?.code && ERRORS[detail.code]?.(detail.missing)) || 'Transition not allowed.')
    }
  }

  const actions = currentStatus?.category !== 'final' && nextStatuses.length > 0 && (
    <div className="space-y-1.5">
      <SectionLabel>Move to</SectionLabel>
      <div className="flex items-center gap-2 flex-wrap">
        {nextStatuses.map(s => (
          <Button key={s.id} size="sm"
            variant={isBackward(s.id) ? 'ghost' : 'outline'}
            className="h-7 text-xs"
            disabled={transition.isPending}
            onClick={() => isBackward(s.id) ? setConfirming(s.id) : perform(s.id)}>
            {isBackward(s.id) ? '← ' : ''}{s.name}
          </Button>
        ))}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )

  const confirm = confirming && (
    <div className="rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 p-3 space-y-2">
      <p className="text-sm font-medium">
        Move back to <strong>{statuses.find(s => s.id === confirming)?.name}</strong>?
      </p>
      <p className="text-xs text-muted-foreground">Backward transitions can lose progress.</p>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={() => setConfirming(null)}>Cancel</Button>
        <Button size="sm" onClick={() => perform(confirming)}>Confirm</Button>
      </div>
    </div>
  )

  if (!actions && !confirm) return null
  if (mode === 'page') {
    return <div className="space-y-3 py-4 border-y">{actions}{confirm}</div>
  }
  return (
    <>
      {actions && <div className="py-3 border-y">{actions}</div>}
      {confirm}
    </>
  )
}
