import { useState } from 'react'
import { Download, Pencil, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/shared/api/client'
import type { Task } from '@/features/tasks/api'
import {
  useIssueWorkPackage, useSaveWorkPackageDraft, useWorkPackage,
  type Criterion, type PackageInput, type WorkPackageContent,
} from './api'
import { SectionLabel, StateBadge } from './ui'
import { inputCls } from './format'

const EMPTY: WorkPackageContent = {
  goal: '', expected_result: '', criteria: [], inputs: [], constraints: [], specialization: '',
}

interface Props {
  task: Task
  /** Reporter or project manager — may edit and issue the assignment. */
  canEdit: boolean
}

/** Task assignment: goal, expected result, criteria, inputs, constraints (ADR-020, TT-09). */
export function WorkPackagePanel({ task, canEdit }: Props) {
  const { data } = useWorkPackage(task.id)
  const [editing, setEditing] = useState(false)
  if (!data) return null

  const current = data.current
  const shown = current?.content ?? data.draft

  async function exportYaml() {
    if (!current) return
    const r = await api.get(`/work-packages/${current.id}/export`, { params: { format: 'yaml' }, responseType: 'blob' })
    const url = URL.createObjectURL(r.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${task.key}-v${current.version}.yaml`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-2" data-testid="work-package">
      <div className="flex items-center gap-2">
        <SectionLabel className="mb-0">Assignment</SectionLabel>
        <StateBadge state={data.state} />
        {current && <span className="text-[11px] text-muted-foreground">v{current.version} · {current.digest.slice(0, 8)}</span>}
        <div className="ml-auto flex gap-1">
          {current && (
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={exportYaml} title="Pinned copy for console agents">
              <Download className="h-3 w-3 mr-1" />YAML
            </Button>
          )}
          {canEdit && !editing && (
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={() => setEditing(true)}>
              <Pencil className="h-3 w-3 mr-1" />{data.state === 'none' ? 'Write' : 'Edit'}
            </Button>
          )}
        </div>
      </div>

      {editing ? (
        <DraftEditor task={task} initial={data.draft ?? current?.content ?? EMPTY} onDone={() => setEditing(false)} />
      ) : shown ? (
        <PackageView content={shown} />
      ) : (
        <p className="text-sm text-muted-foreground italic">
          No assignment yet — the task is not ready for execution.
        </p>
      )}
    </div>
  )
}

function PackageView({ content }: { content: WorkPackageContent }) {
  return (
    <div className="rounded-lg border p-3 space-y-2 text-sm">
      {content.goal && <p><span className="text-muted-foreground text-xs">Goal: </span>{content.goal}</p>}
      {content.expected_result && <p><span className="text-muted-foreground text-xs">Result: </span>{content.expected_result}</p>}
      {content.specialization && <p><span className="text-muted-foreground text-xs">Specialization: </span>{content.specialization}</p>}
      {content.criteria.length > 0 && (
        <ul className="space-y-0.5">
          {content.criteria.map((c, i) => (
            <li key={c.key ?? i} className="flex gap-2">
              <span className="font-mono text-[11px] text-muted-foreground w-6 shrink-0">{c.key ?? '·'}</span>
              <span className="flex-1">{c.text}</span>
              {!c.required && <span className="text-[10px] text-muted-foreground">optional</span>}
            </li>
          ))}
        </ul>
      )}
      {content.inputs.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Inputs: {content.inputs.map(i => `${i.kind}: ${i.ref}${i.version ? `@${i.version}` : ''}`).join('; ')}
        </p>
      )}
      {content.constraints.length > 0 && (
        <p className="text-xs text-muted-foreground">Constraints: {content.constraints.join('; ')}</p>
      )}
    </div>
  )
}

function DraftEditor({ task, initial, onDone }: { task: Task; initial: WorkPackageContent; onDone: () => void }) {
  const [draft, setDraft] = useState<WorkPackageContent>({
    ...EMPTY, ...initial,
    criteria: initial.criteria.map(c => ({ ...c })),
    inputs: initial.inputs.map(i => ({ ...i })),
  })
  const [constraintsText, setConstraintsText] = useState(initial.constraints.join('\n'))
  const save = useSaveWorkPackageDraft(task.id)
  const issue = useIssueWorkPackage(task)
  const set = <K extends keyof WorkPackageContent>(k: K, v: WorkPackageContent[K]) => setDraft(d => ({ ...d, [k]: v }))

  const setCriterion = (i: number, patch: Partial<Criterion>) =>
    set('criteria', draft.criteria.map((c, j) => (j === i ? { ...c, ...patch } : c)))
  const setInput = (i: number, patch: Partial<PackageInput>) =>
    set('inputs', draft.inputs.map((x, j) => (j === i ? { ...x, ...patch } : x)))

  const content = (): WorkPackageContent => ({
    ...draft,
    constraints: constraintsText.split('\n').map(l => l.trim()).filter(Boolean),
  })
  async function saveDraft() {
    await save.mutateAsync(content())
  }
  async function saveAndIssue() {
    await save.mutateAsync(content())
    await issue.mutateAsync()
    onDone()
  }

  return (
    <div className="rounded-lg border p-3 space-y-2.5 text-sm">
      <textarea aria-label="Goal" className={inputCls} rows={2} placeholder="Goal"
        value={draft.goal ?? ''} onChange={e => set('goal', e.target.value)} />
      <textarea aria-label="Expected result" className={inputCls} rows={2} placeholder="Expected result"
        value={draft.expected_result ?? ''} onChange={e => set('expected_result', e.target.value)} />
      <input aria-label="Specialization" className={inputCls} placeholder="Specialization (e.g. backend)"
        value={draft.specialization ?? ''} onChange={e => set('specialization', e.target.value)} />

      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">Acceptance criteria</p>
        {draft.criteria.map((c, i) => (
          <div key={i} className="flex gap-1.5 items-center">
            <input aria-label={`Criterion ${i + 1}`} className={inputCls} value={c.text}
              onChange={e => setCriterion(i, { text: e.target.value })} />
            <label className="flex items-center gap-1 text-[11px] text-muted-foreground whitespace-nowrap">
              <input type="checkbox" checked={c.required} onChange={e => setCriterion(i, { required: e.target.checked })} />
              required
            </label>
            <button onClick={() => set('criteria', draft.criteria.filter((_, j) => j !== i))} aria-label="Remove criterion">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
        ))}
        <Button size="sm" variant="ghost" className="h-6 px-2 text-xs"
          onClick={() => set('criteria', [...draft.criteria, { text: '', required: true }])}>
          <Plus className="h-3 w-3 mr-1" />Criterion
        </Button>
      </div>

      <div className="space-y-1">
        <p className="text-xs text-muted-foreground">Inputs</p>
        {draft.inputs.map((x, i) => (
          <div key={i} className="flex gap-1.5 items-center">
            <input aria-label="Input kind" className={`${inputCls} w-28`} placeholder="kind" value={x.kind}
              onChange={e => setInput(i, { kind: e.target.value })} />
            <input aria-label="Input ref" className={inputCls} placeholder="reference" value={x.ref}
              onChange={e => setInput(i, { ref: e.target.value })} />
            <input aria-label="Input version" className={`${inputCls} w-24`} placeholder="version" value={x.version ?? ''}
              onChange={e => setInput(i, { version: e.target.value || null })} />
            <button onClick={() => set('inputs', draft.inputs.filter((_, j) => j !== i))} aria-label="Remove input">
              <X className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </div>
        ))}
        <Button size="sm" variant="ghost" className="h-6 px-2 text-xs"
          onClick={() => set('inputs', [...draft.inputs, { kind: 'document', ref: '' }])}>
          <Plus className="h-3 w-3 mr-1" />Input
        </Button>
      </div>

      <textarea aria-label="Constraints" className={inputCls} rows={2} placeholder="Constraints, one per line"
        value={constraintsText} onChange={e => setConstraintsText(e.target.value)} />

      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={saveDraft} disabled={save.isPending}>Save draft</Button>
        <Button size="sm" onClick={saveAndIssue} disabled={save.isPending || issue.isPending}>Issue version</Button>
        <Button size="sm" variant="ghost" onClick={onDone}>Cancel</Button>
      </div>
    </div>
  )
}
