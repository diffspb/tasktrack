import { useState } from 'react'
import { X } from 'lucide-react'
import { useUpdateTask, type Task } from '../api'
import { fmtDate } from './constants'
import { SectionLabel } from './ui'

function DateField({ label, value, onChange }: {
  label: string; value: string | null; onChange: (v: string | null) => Promise<unknown>
}) {
  const [editing, setEditing] = useState(false)
  return (
    <div className="flex items-center gap-2 py-1.5">
      <span className="text-[11px] text-muted-foreground w-20 shrink-0">{label}</span>
      {editing ? (
        <input
          type="date"
          autoFocus
          defaultValue={value ?? ''}
          className="text-xs border rounded px-1.5 py-0.5 bg-background"
          onChange={async e => {
            const val = e.target.value
            setEditing(false)
            await onChange(val || null)
          }}
          onKeyDown={e => { if (e.key === 'Escape') setEditing(false) }}
          onBlur={() => setEditing(false)}
        />
      ) : (
        <div className="flex items-center gap-1">
          <button
            className="text-xs text-left hover:underline cursor-pointer text-muted-foreground hover:text-foreground"
            onClick={() => setEditing(true)}
          >
            {value ? fmtDate(value) : <span className="italic">Not set</span>}
          </button>
          {value && (
            <button className="text-muted-foreground/40 hover:text-muted-foreground" onClick={() => onChange(null)}>
              <X className="h-3 w-3" />
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export function DatesBlock({ task }: { task: Task }) {
  const updateTask = useUpdateTask(task.id, task.project_id)
  return (
    <div className="space-y-2">
      <SectionLabel>Dates</SectionLabel>
      <div className="space-y-0.5 text-sm">
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Created</span>
          <span className="text-xs text-muted-foreground">{fmtDate(task.created_at)}</span>
        </div>
        <div className="flex items-center gap-2 py-1.5">
          <span className="text-[11px] text-muted-foreground w-20 shrink-0">Updated</span>
          <span className="text-xs text-muted-foreground">{fmtDate(task.updated_at)}</span>
        </div>
        <DateField label="Start date" value={task.start_date}
          onChange={v => updateTask.mutateAsync({ start_date: v, version: task.version })} />
        <DateField label="Due date" value={task.due_date}
          onChange={v => updateTask.mutateAsync({ due_date: v, version: task.version })} />
      </div>
    </div>
  )
}
