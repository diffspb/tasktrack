import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Pill, SectionLabel } from '@/features/results/ui'
import { fmtDateTime, inputCls } from '@/features/results/format'
import {
  useBases, useDecideImpact, useImpactAssessments, useReadiness,
  type Basis, type ImpactAssessment, type ImpactDecisionBody, type ReadinessCondition,
} from './api'

const CONDITION_LABEL: Record<ReadinessCondition['key'], string> = {
  package:   'Assignment and assignee',
  inputs:    'Inputs accepted',
  normative: 'Normative bases',
  grant:     'Allocation / authorization',
  blockers:  'No blockers or unresolved changes',
}

const ROLE_LABEL: Record<Basis['role'], string> = {
  cause: 'cause', input: 'input', normative: 'normative', reference: 'reference', grant: 'grant',
}

/**
 * Portfolio readiness (ADR-024, TT-10/11): the task's bases with pinned revisions and the
 * five conditions for starting execution. A standalone project shows nothing — its local
 * process applies. Facts are imported through the API; the manager decides impact here.
 */
export function ReadinessPanel({ taskId, isManager }: { taskId: string; isManager: boolean }) {
  const { data: readiness } = useReadiness(taskId)
  const portfolio = readiness?.mode === 'portfolio'
  const { data: bases = [] } = useBases(taskId, portfolio)
  const { data: assessments = [] } = useImpactAssessments(taskId, portfolio)
  if (!readiness || !portfolio) return null
  const pending = assessments.filter(a => a.status === 'pending')

  return (
    <div className="space-y-2" data-testid="readiness-panel">
      <SectionLabel>Readiness</SectionLabel>
      <div className="rounded-lg border p-3 space-y-2 text-sm">
        <div className="flex items-center gap-2 text-xs">
          <Pill tone={readiness.ready ? 'success' : 'warning'}>{readiness.ready ? 'Ready to start' : 'Waiting'}</Pill>
          <span className="text-muted-foreground">checked {fmtDateTime(readiness.checked_at)}</span>
        </div>
        <ul className="space-y-1">
          {readiness.conditions.map(c => (
            <li key={c.key} className="text-xs">
              <span className={c.ok ? 'text-green-700 dark:text-green-400' : 'text-amber-700 dark:text-amber-400'}>
                {c.ok ? '✓' : '•'}
              </span>{' '}
              {CONDITION_LABEL[c.key]}
              {c.reasons.map((r, i) => (
                <p key={i} className="ml-3 text-muted-foreground" title={r.code}>
                  {r.message}{r.as_of ? ` (as of ${fmtDateTime(r.as_of)})` : ''}
                </p>
              ))}
            </li>
          ))}
        </ul>
      </div>

      {bases.length > 0 && (
        <ul className="space-y-1 text-xs" aria-label="Bases">
          {bases.map(b => (
            <li key={b.id} className="flex flex-wrap items-center gap-1.5">
              <Pill tone={b.role === 'reference' ? 'muted' : 'neutral'}>{ROLE_LABEL[b.role]}</Pill>
              <span>{b.object.type}/{b.object.ext_id}@{b.revision}</span>
              {b.object.is_training && <Pill tone="muted">training</Pill>}
              {!b.verified && <Pill tone="warning">unverified</Pill>}
              {b.object.status === 'revoked' && <Pill tone="danger">revoked</Pill>}
              {b.object.current_revision && b.object.current_revision !== b.revision && (
                <Pill tone="warning">current {b.object.current_revision}</Pill>
              )}
              {b.evidence.map(e => (
                <Pill key={e.id} tone="info">{String(e.claims.kind ?? 'evidence')}: {String(e.claims.outcome ?? '—')}</Pill>
              ))}
            </li>
          ))}
        </ul>
      )}

      {pending.map(a => <ImpactItem key={a.id} taskId={taskId} assessment={a} canDecide={isManager} />)}
    </div>
  )
}

function ImpactItem({ taskId, assessment, canDecide }: { taskId: string; assessment: ImpactAssessment; canDecide: boolean }) {
  const decide = useDecideImpact(taskId)
  const [rationale, setRationale] = useState('')
  const [authority, setAuthority] = useState('')
  const send = (decision: ImpactDecisionBody['decision']) =>
    decide.mutate({ id: assessment.id, body: { decision, rationale, ...(authority ? { authority } : {}) } })

  return (
    <div className="rounded-lg border border-amber-300 p-3 space-y-2 text-xs" data-testid="impact-assessment">
      <p>New revision of a basis: {assessment.old_revision} → {assessment.new_revision}. Impact decision needed.</p>
      {canDecide && (
        <>
          <input aria-label="Rationale" className={inputCls} placeholder="Rationale" value={rationale}
            onChange={e => setRationale(e.target.value)} />
          <input aria-label="Authority" className={inputCls} placeholder="Authority (required to continue)"
            value={authority} onChange={e => setAuthority(e.target.value)} />
          <div className="flex flex-wrap gap-1.5">
            <Button size="sm" variant="outline" disabled={!rationale.trim() || !authority.trim()} onClick={() => send('continue')}>
              Continue on old
            </Button>
            <Button size="sm" variant="outline" disabled={!rationale.trim()} onClick={() => send('reissue')}>Reissue</Button>
            <Button size="sm" variant="outline" disabled={!rationale.trim()} onClick={() => send('recheck')}>Recheck</Button>
            <Button size="sm" variant="destructive" disabled={!rationale.trim()} onClick={() => send('stop')}>Stop</Button>
          </div>
        </>
      )}
    </div>
  )
}
