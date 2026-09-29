import { useState } from 'react'
import { ExternalLink, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { ProjectMember, Task } from '@/features/tasks/api'
import {
  useProposals, useProposeDelivery, useRecordRecipientAcceptance, useReviewProposal,
  useSubmitProposal, useWithdrawProposal, useWorkPackage,
  type Proposal, type ProposalCheck, type ProposalCriterion, type ProposalLink, type Verdict,
} from './api'
import { Pill, SectionLabel, StateBadge } from './ui'
import { fmtDateTime, inputCls } from './format'

interface Props {
  task: Task
  currentUserId: string
  members: ProjectMember[]
}

/**
 * Result proposals and independent review (ADR-016, ADR-021, FR-003 TT-14–17).
 * The assignee submits results; a member with the reviewer profile — never the
 * author or the assignee — reviews them. Comments are discussion, not results.
 */
export function ResultSection({ task, currentUserId, members }: Props) {
  const { data: proposals = [] } = useProposals(task.id)
  const { data: pkg } = useWorkPackage(task.id)
  const [submitting, setSubmitting] = useState(false)

  const me = members.find(m => m.user.id === currentUserId)
  const nameOf = (id: string) => members.find(m => m.user.id === id)?.user.display_name ?? id.slice(0, 8)
  const isAssignee = task.assignee_id === currentUserId
  const isManager = me?.role === 'admin' || me?.role === 'manager'
  const canReview = (p: Proposal) =>
    p.status === 'submitted' && !!me?.is_reviewer && me.role !== 'viewer'
    && p.author_id !== currentUserId && task.assignee_id !== currentUserId
    && (!task.reviewer_id || task.reviewer_id === currentUserId)

  const criteria = pkg?.current?.content.criteria ?? []
  const openVersion = [...proposals].reverse().find(p => p.status === 'submitted' || p.status === 'changes_requested')
  const ordered = [...proposals].sort((a, b) => b.version - a.version)

  return (
    <div className="space-y-2" data-testid="result-section">
      <div className="flex items-center gap-2">
        <SectionLabel className="mb-0">Result</SectionLabel>
        <StateBadge state={task.result_state} />
        {task.reviewer_id && (
          <span className="text-[11px] text-muted-foreground">reviewer: {nameOf(task.reviewer_id)}</span>
        )}
        {isAssignee && !submitting && (
          <Button size="sm" variant="ghost" className="ml-auto h-6 px-2 text-xs" onClick={() => setSubmitting(true)}>
            <Plus className="h-3 w-3 mr-1" />{openVersion ? 'New version' : 'Submit result'}
          </Button>
        )}
      </div>

      {submitting && (
        <ProposalForm
          task={task}
          criteria={criteria.map(c => c.key)}
          supersedes={openVersion}
          onDone={() => setSubmitting(false)}
        />
      )}

      {ordered.length === 0 && !submitting && (
        <p className="text-sm text-muted-foreground italic">No result submitted yet.</p>
      )}

      <ul className="space-y-2">
        {ordered.map(p => (
          <li key={p.id} className="rounded-lg border p-3 space-y-2 text-sm" data-testid={`proposal-v${p.version}`}>
            <ProposalView proposal={p} authorName={nameOf(p.author_id)} />
            <ReviewsView proposal={p} nameOf={nameOf} />
            <div className="flex gap-2">
              {p.author_id === currentUserId && p.status === 'submitted' && <WithdrawButton task={task} proposal={p} />}
            </div>
            {canReview(p) && <ReviewForm task={task} proposal={p} packageCriteria={criteria} />}
          </li>
        ))}
      </ul>

      {task.result_state === 'accepted' && (
        <DeliveryBlock task={task} canPropose={isAssignee || isManager} canRecord={isManager} />
      )}
    </div>
  )
}

function ProposalView({ proposal: p, authorName }: { proposal: Proposal; authorName: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="font-semibold text-foreground">v{p.version}</span>
        <StateBadge state={p.status} />
        <span>{authorName}</span>
        <span>· {fmtDateTime(p.created_at)}</span>
        {p.session_id && <Pill tone="muted">session</Pill>}
      </div>
      <p className="whitespace-pre-wrap">{p.summary}</p>
      {p.links.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {p.links.map((l, i) => (
            <li key={i}>
              <a href={l.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                {l.kind}{l.ref ? ` ${l.ref}` : ''} <ExternalLink className="h-3 w-3" />
              </a>
            </li>
          ))}
        </ul>
      )}
      {p.criteria.length > 0 && (
        <ul className="text-xs space-y-0.5">
          {p.criteria.map(c => (
            <li key={c.key} className="flex gap-2">
              <span className="font-mono text-muted-foreground w-6">{c.key}</span>
              <Pill tone={c.status === 'met' ? 'success' : c.status === 'not_met' ? 'danger' : 'muted'}>{c.status}</Pill>
              {c.evidence && <span className="text-muted-foreground">{c.evidence}</span>}
            </li>
          ))}
        </ul>
      )}
      {p.checks.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Checks: {p.checks.map(c => `${c.name} — ${c.result}`).join('; ')}
        </p>
      )}
      {p.limitations && <p className="text-xs text-muted-foreground">Limitations: {p.limitations}</p>}
    </div>
  )
}

function ReviewsView({ proposal, nameOf }: { proposal: Proposal; nameOf: (id: string) => string }) {
  if (proposal.reviews.length === 0) return null
  return (
    <ul className="space-y-1.5 border-l-2 pl-3">
      {proposal.reviews.map(r => (
        <li key={r.id} className="text-xs space-y-0.5">
          <div className="flex items-center gap-2 text-muted-foreground">
            <StateBadge state={r.verdict} />
            <span>{nameOf(r.reviewer_id)} · {fmtDateTime(r.created_at)}</span>
          </div>
          <p className="whitespace-pre-wrap text-foreground">{r.rationale}</p>
          {r.criteria.filter(c => c.note).map(c => (
            <p key={c.key} className="text-muted-foreground"><span className="font-mono">{c.key}</span>: {c.note}</p>
          ))}
        </li>
      ))}
    </ul>
  )
}

function WithdrawButton({ task, proposal }: { task: Task; proposal: Proposal }) {
  const withdraw = useWithdrawProposal(task)
  return (
    <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" disabled={withdraw.isPending}
      onClick={() => withdraw.mutate(proposal.id)}>
      Withdraw
    </Button>
  )
}

function ProposalForm({ task, criteria, supersedes, onDone }: {
  task: Task; criteria: string[]; supersedes?: Proposal; onDone: () => void
}) {
  const submit = useSubmitProposal(task)
  const [summary, setSummary] = useState('')
  const [limitations, setLimitations] = useState('')
  const [links, setLinks] = useState<ProposalLink[]>([])
  const [checks, setChecks] = useState<ProposalCheck[]>([])
  const [crit, setCrit] = useState<ProposalCriterion[]>(criteria.map(key => ({ key, status: 'met' })))

  async function send() {
    await submit.mutateAsync({
      summary, limitations: limitations || null,
      links: links.filter(l => l.url.trim()),
      checks: checks.filter(c => c.name.trim()),
      criteria: crit,
      supersedes_id: supersedes?.id ?? null,
    })
    onDone()
  }

  return (
    <div className="rounded-lg border border-primary/30 p-3 space-y-2.5 text-sm">
      {supersedes && (
        <p className="text-xs text-muted-foreground">Replaces v{supersedes.version}; the new version needs a new review.</p>
      )}
      <textarea aria-label="Result summary" className={inputCls} rows={3} placeholder="What was done"
        value={summary} onChange={e => setSummary(e.target.value)} />

      {crit.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">Criteria of the assignment</p>
          {crit.map((c, i) => (
            <div key={c.key} className="flex gap-1.5 items-center">
              <span className="font-mono text-xs w-6">{c.key}</span>
              <select aria-label={`Criterion ${c.key}`} className={`${inputCls} w-36`} value={c.status}
                onChange={e => setCrit(crit.map((x, j) => j === i ? { ...x, status: e.target.value as ProposalCriterion['status'] } : x))}>
                <option value="met">met</option>
                <option value="not_met">not met</option>
                <option value="not_applicable">n/a</option>
              </select>
              <input aria-label={`Evidence ${c.key}`} className={inputCls} placeholder="evidence" value={c.evidence ?? ''}
                onChange={e => setCrit(crit.map((x, j) => j === i ? { ...x, evidence: e.target.value || null } : x))} />
            </div>
          ))}
        </div>
      )}

      <div className="space-y-1">
        {links.map((l, i) => (
          <div key={i} className="flex gap-1.5 items-center">
            <select aria-label="Link kind" className={`${inputCls} w-28`} value={l.kind}
              onChange={e => setLinks(links.map((x, j) => j === i ? { ...x, kind: e.target.value as ProposalLink['kind'] } : x))}>
              {['pr', 'commit', 'release', 'build', 'document', 'other'].map(k => <option key={k} value={k}>{k}</option>)}
            </select>
            <input aria-label="Link URL" className={inputCls} placeholder="https://…" value={l.url}
              onChange={e => setLinks(links.map((x, j) => j === i ? { ...x, url: e.target.value } : x))} />
            <button onClick={() => setLinks(links.filter((_, j) => j !== i))} aria-label="Remove link">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
        ))}
        {checks.map((c, i) => (
          <div key={i} className="flex gap-1.5 items-center">
            <input aria-label="Check name" className={inputCls} placeholder="check (e.g. tests)" value={c.name}
              onChange={e => setChecks(checks.map((x, j) => j === i ? { ...x, name: e.target.value } : x))} />
            <select aria-label="Check result" className={`${inputCls} w-28`} value={c.result}
              onChange={e => setChecks(checks.map((x, j) => j === i ? { ...x, result: e.target.value as ProposalCheck['result'] } : x))}>
              {['passed', 'failed', 'skipped'].map(k => <option key={k} value={k}>{k}</option>)}
            </select>
            <button onClick={() => setChecks(checks.filter((_, j) => j !== i))} aria-label="Remove check">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
        ))}
        <div className="flex gap-1">
          <Button size="sm" variant="ghost" className="h-6 px-2 text-xs"
            onClick={() => setLinks([...links, { kind: 'pr', url: '' }])}><Plus className="h-3 w-3 mr-1" />Link</Button>
          <Button size="sm" variant="ghost" className="h-6 px-2 text-xs"
            onClick={() => setChecks([...checks, { name: '', result: 'passed' }])}><Plus className="h-3 w-3 mr-1" />Check</Button>
        </div>
      </div>

      <textarea aria-label="Limitations" className={inputCls} rows={2} placeholder="Known limitations (optional)"
        value={limitations} onChange={e => setLimitations(e.target.value)} />

      <div className="flex gap-2">
        <Button size="sm" onClick={send} disabled={!summary.trim() || submit.isPending}>Submit</Button>
        <Button size="sm" variant="ghost" onClick={onDone}>Cancel</Button>
      </div>
    </div>
  )
}

function ReviewForm({ task, proposal, packageCriteria }: {
  task: Task; proposal: Proposal; packageCriteria: { key: string; text: string; required: boolean }[]
}) {
  const review = useReviewProposal(task)
  const keys = packageCriteria.length > 0
    ? packageCriteria
    : proposal.criteria.map(c => ({ key: c.key, text: c.evidence ?? '', required: true }))
  const [verdict, setVerdict] = useState<Verdict>('accepted')
  const [rationale, setRationale] = useState('')
  const [crit, setCrit] = useState(keys.map(k => ({ key: k.key, verdict: 'met' as 'met' | 'not_met', note: '' })))

  return (
    <div className="rounded-md bg-muted/40 p-2.5 space-y-2" data-testid="review-form">
      <p className="text-xs font-medium">Review v{proposal.version}</p>
      {crit.map((c, i) => (
        <div key={c.key} className="flex gap-1.5 items-center text-xs">
          <span className="font-mono w-6">{c.key}</span>
          <span className="flex-1 truncate text-muted-foreground">{keys[i].text}</span>
          <select aria-label={`Verdict ${c.key}`} className={`${inputCls} w-24`} value={c.verdict}
            onChange={e => setCrit(crit.map((x, j) => j === i ? { ...x, verdict: e.target.value as 'met' | 'not_met' } : x))}>
            <option value="met">met</option>
            <option value="not_met">not met</option>
          </select>
          <input aria-label={`Note ${c.key}`} className={`${inputCls} w-40`} placeholder="note" value={c.note}
            onChange={e => setCrit(crit.map((x, j) => j === i ? { ...x, note: e.target.value } : x))} />
        </div>
      ))}
      <select aria-label="Verdict" className={inputCls} value={verdict} onChange={e => setVerdict(e.target.value as Verdict)}>
        <option value="accepted">Accept</option>
        <option value="changes_requested">Request changes</option>
        <option value="rejected">Reject (reasoned refusal)</option>
      </select>
      <textarea aria-label="Rationale" className={inputCls} rows={2} placeholder="Rationale (required)"
        value={rationale} onChange={e => setRationale(e.target.value)} />
      <Button size="sm" disabled={!rationale.trim() || review.isPending}
        onClick={() => review.mutate({
          proposalId: proposal.id, verdict, rationale,
          criteria: crit.map(c => ({ key: c.key, verdict: c.verdict, note: c.note || null })),
        })}>
        Submit review
      </Button>
    </div>
  )
}

function DeliveryBlock({ task, canPropose, canRecord }: { task: Task; canPropose: boolean; canRecord: boolean }) {
  const propose = useProposeDelivery(task)
  const record = useRecordRecipientAcceptance(task)
  const [target, setTarget] = useState('')
  const [ref, setRef] = useState('')
  const [by, setBy] = useState('')

  return (
    <div className="rounded-lg border p-3 space-y-2 text-sm">
      <p className="text-xs text-muted-foreground">
        Local review accepted the result. Delivery to another project and its acceptance are separate facts.
      </p>
      {task.delivery ? (
        <p className="text-xs">Delivery proposed to <strong>{task.delivery.target}</strong>{task.delivery.ref ? ` (${task.delivery.ref})` : ''}</p>
      ) : canPropose && (
        <div className="flex gap-1.5">
          <input aria-label="Delivery target" className={inputCls} placeholder="Recipient (project, process)" value={target}
            onChange={e => setTarget(e.target.value)} />
          <input aria-label="Delivery ref" className={`${inputCls} w-32`} placeholder="ref" value={ref}
            onChange={e => setRef(e.target.value)} />
          <Button size="sm" disabled={!target.trim() || propose.isPending}
            onClick={() => propose.mutate({ target, ref: ref || null })}>Propose</Button>
        </div>
      )}
      {task.recipient_acceptance ? (
        <p className="text-xs">
          <Pill tone="success">Recipient accepted</Pill>{' '}
          {task.recipient_acceptance.accepted_by} · {task.recipient_acceptance.accepted_at}
          {task.recipient_acceptance.ref ? ` (${task.recipient_acceptance.ref})` : ''}
        </p>
      ) : task.delivery && canRecord && (
        <div className="flex gap-1.5">
          <input aria-label="Accepted by" className={inputCls} placeholder="Accepted by (from the recipient)" value={by}
            onChange={e => setBy(e.target.value)} />
          <Button size="sm" disabled={!by.trim() || record.isPending}
            onClick={() => record.mutate({ accepted_by: by, accepted_at: new Date().toISOString(), source: 'manual' })}>
            Record acceptance
          </Button>
        </div>
      )}
    </div>
  )
}
