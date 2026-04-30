import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  useAssignUser,
  useProjectMembers,
  type Assignment,
  type AssigneeRole,
} from '@/features/tasks/api'

const ROLES: { value: AssigneeRole; label: string }[] = [
  { value: 'lead', label: 'Lead' },
  { value: 'reviewer', label: 'Reviewer' },
  { value: 'consultant', label: 'Consultant' },
]

interface Props {
  projectId: string
  taskId: string
  assignments: Assignment[]
  canEdit: boolean
}

export function AssigneePicker({ projectId, taskId, assignments, canEdit }: Props) {
  const { data: members } = useProjectMembers(projectId)
  const assignUser = useAssignUser(projectId)
  const [adding, setAdding] = useState(false)
  const [pickedUser, setPickedUser] = useState<string>('')
  const [pickedRole, setPickedRole] = useState<AssigneeRole>('lead')
  const [error, setError] = useState<string | null>(null)

  if (!canEdit) return null

  const assignedIds = new Set(assignments.map(a => a.user_id))
  const candidates = (members?.items ?? []).filter(m => !assignedIds.has(m.user.id))

  async function handleAdd() {
    if (!pickedUser) return
    setError(null)
    try {
      await assignUser.mutateAsync({ taskId, userId: pickedUser, role: pickedRole })
      setPickedUser('')
      setPickedRole('lead')
      setAdding(false)
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      setError(code ?? 'Failed to assign')
    }
  }

  if (!adding) {
    return candidates.length === 0 ? null : (
      <Button size="sm" variant="ghost" className="h-7 gap-1 text-xs" onClick={() => setAdding(true)}>
        <Plus className="h-3 w-3" /> Add assignee
      </Button>
    )
  }

  return (
    <div className="space-y-2 rounded-md border bg-muted/20 p-2.5">
      <div className="flex items-center gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Add assignee
        </p>
        <div className="flex-1" />
        <Button size="icon" variant="ghost" className="h-6 w-6" onClick={() => { setAdding(false); setError(null) }}>
          <X className="h-3 w-3" />
        </Button>
      </div>
      <select
        value={pickedUser}
        onChange={e => setPickedUser(e.target.value)}
        disabled={assignUser.isPending}
        className="w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
      >
        <option value="">Select user…</option>
        {candidates.map(m => (
          <option key={m.user.id} value={m.user.id}>{m.user.display_name}</option>
        ))}
      </select>
      <div className="flex gap-1.5">
        {ROLES.map(r => (
          <button
            key={r.value}
            type="button"
            onClick={() => setPickedRole(r.value)}
            className={`flex-1 rounded-md border px-2 py-1 text-xs transition-colors ${
              pickedRole === r.value
                ? 'border-primary bg-primary/10 text-primary font-medium'
                : 'border-border text-muted-foreground hover:border-ring/50'
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
      <Button size="sm" onClick={handleAdd} disabled={!pickedUser || assignUser.isPending}>
        {assignUser.isPending ? 'Adding…' : 'Add'}
      </Button>
    </div>
  )
}

export function AssigneeBadgeRole({ role }: { role: AssigneeRole }) {
  return <Badge variant="outline" className="text-[10px] capitalize h-5">{role}</Badge>
}
