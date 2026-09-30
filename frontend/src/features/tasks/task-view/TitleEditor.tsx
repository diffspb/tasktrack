import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useUpdateTask, type Task } from '../api'

export function TitleEditor({ task, mode }: { task: Task; mode: 'page' | 'panel' }) {
  const updateTask = useUpdateTask(task.id, task.project_id)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  async function save() {
    const trimmed = draft.trim()
    setEditing(false)
    if (trimmed && trimmed !== task.title) {
      await updateTask.mutateAsync({ title: trimmed, version: task.version })
    }
  }

  if (editing) {
    return (
      <div className="space-y-2">
        <input
          autoFocus
          value={draft}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter') save()
            if (e.key === 'Escape') setEditing(false)
          }}
          onBlur={save}
          className={cn(
            'w-full font-semibold bg-transparent border-b-2 border-primary outline-none leading-snug',
            mode === 'page' ? 'text-2xl' : 'text-base',
          )}
        />
        <div className="flex gap-2">
          <Button size="sm" onMouseDown={e => e.preventDefault()} onClick={save}>Save</Button>
          <Button size="sm" variant="ghost"
            onMouseDown={e => e.preventDefault()}
            onClick={() => setEditing(false)}
          >Cancel</Button>
        </div>
      </div>
    )
  }

  return (
    <h1
      onClick={() => { setDraft(task.title); setEditing(true) }}
      className={cn(
        'font-semibold leading-snug cursor-text rounded px-1 -mx-1',
        'hover:bg-muted/40 transition-colors',
        mode === 'page' ? 'text-2xl' : 'text-base',
      )}
    >
      {task.title}
    </h1>
  )
}
