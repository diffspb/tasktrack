import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useUpdateTask, type Task } from '../api'
import { SectionLabel } from './ui'

export function DescriptionEditor({ task }: { task: Task }) {
  const updateTask = useUpdateTask(task.id, task.project_id)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  async function save() {
    const val = draft.trim() || null
    setEditing(false)
    if (val !== (task.description ?? null)) {
      await updateTask.mutateAsync({ description: val ?? undefined, version: task.version })
    }
  }

  return (
    <div className="space-y-2">
      <SectionLabel>Description</SectionLabel>
      {editing ? (
        <div className="space-y-2">
          <textarea
            autoFocus
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === 'Escape') setEditing(false) }}
            onBlur={save}
            rows={Math.max(4, draft.split('\n').length + 1)}
            placeholder="Add a description…"
            className="w-full text-sm bg-transparent border border-border rounded-md px-3 py-2 outline-none focus:border-primary resize-none leading-relaxed"
          />
          <div className="flex gap-2">
            <Button size="sm" onMouseDown={e => e.preventDefault()} onClick={save}>Save</Button>
            <Button size="sm" variant="ghost"
              onMouseDown={e => e.preventDefault()}
              onClick={() => setEditing(false)}
            >Cancel</Button>
          </div>
        </div>
      ) : (
        <div
          onClick={() => { setDraft(task.description ?? ''); setEditing(true) }}
          className="cursor-text rounded-md px-2.5 py-2 -mx-2.5 hover:bg-muted/40 transition-colors min-h-10"
        >
          {task.description
            ? <p className="text-sm whitespace-pre-wrap leading-relaxed">{task.description}</p>
            : <p className="text-sm text-muted-foreground italic">Add a description…</p>}
        </div>
      )}
    </div>
  )
}
