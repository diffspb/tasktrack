import { useEffect, useState } from 'react'
import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { Plus, X } from 'lucide-react'
import { useDecisionCriteria, useReplaceCriteria } from '@/features/tasks/api'

interface Props {
  projectId: string
  taskId: string
  canEdit: boolean
}

export function DecisionCriteriaPanel({ projectId, taskId, canEdit }: Props) {
  const { data, isLoading } = useDecisionCriteria(taskId)
  const replace = useReplaceCriteria(projectId, taskId)
  const [editing, setEditing] = useState(false)
  const [drafts, setDrafts] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (data) setDrafts(data.items.map(c => c.description))
  }, [data?.items])

  if (isLoading) return null

  const items = data?.items ?? []
  const locked = items.length > 0 && items.every(c => c.is_locked)

  async function handleSave() {
    setError(null)
    try {
      await replace.mutateAsync(
        drafts
          .map((description, idx) => ({ description: description.trim(), position: idx }))
          .filter(d => d.description),
      )
      setEditing(false)
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      setError(code ?? 'Save failed')
    }
  }

  if (!editing) {
    if (items.length === 0 && !canEdit) return null
    return (
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Decision criteria
          </p>
          {locked && <span className="text-[10px] text-muted-foreground">locked</span>}
          <div className="flex-1" />
          {canEdit && !locked && (
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={() => setEditing(true)}>
              {items.length === 0 ? 'Add criteria' : 'Edit'}
            </Button>
          )}
        </div>
        {items.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">No criteria set.</p>
        ) : (
          <ol className="list-decimal list-inside space-y-0.5 text-sm">
            {items.map(c => <li key={c.id}>{c.description}</li>)}
          </ol>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2 rounded-md border bg-muted/20 p-2.5">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Decision criteria
      </p>
      <div className="space-y-1.5">
        {drafts.map((d, idx) => (
          <div key={idx} className="flex gap-1.5">
            <input
              value={d}
              onChange={e => {
                const next = [...drafts]
                next[idx] = e.target.value
                setDrafts(next)
              }}
              placeholder={`Criterion ${idx + 1}`}
              className="flex-1 rounded-md border border-input bg-background px-2 py-1 text-sm"
            />
            <Button size="icon" variant="ghost" className="h-7 w-7"
              onClick={() => setDrafts(drafts.filter((_, i) => i !== idx))}>
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
      </div>
      <Button size="sm" variant="outline" className="gap-1 h-7"
        onClick={() => setDrafts([...drafts, ''])}>
        <Plus className="h-3 w-3" /> Add
      </Button>
      {error && <p className="text-xs text-destructive">{error}</p>}
      <div className="flex gap-2">
        <Button size="sm" variant="ghost" onClick={() => {
          setEditing(false); setDrafts(items.map(c => c.description)); setError(null)
        }} disabled={replace.isPending}>
          Cancel
        </Button>
        <Button size="sm" onClick={handleSave} disabled={replace.isPending}>
          {replace.isPending ? 'Saving…' : 'Save criteria'}
        </Button>
      </div>
    </div>
  )
}
