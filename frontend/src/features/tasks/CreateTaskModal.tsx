import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreateTask, useProjectMembers, useProjectEpics, useProjectTaskTypes, type Priority } from './api'

interface Props {
  open: boolean
  projectId: string
  onClose: () => void
}

const PRIORITIES: Priority[] = ['low', 'medium', 'high', 'critical']

export function CreateTaskModal({ open, projectId, onClose }: Props) {
  const [title, setTitle] = useState('')
  const [priority, setPriority] = useState<Priority>('medium')
  const [description, setDescription] = useState('')
  const [typeKey, setTypeKey] = useState('task')
  const [assigneeId, setAssigneeId] = useState('')
  const [parentEpicId, setParentEpicId] = useState('')
  const [error, setError] = useState<string | null>(null)
  const create = useCreateTask(projectId)
  const { data: members } = useProjectMembers(projectId)
  const { data: epics = [] } = useProjectEpics(projectId)
  const { data: taskTypesData } = useProjectTaskTypes(projectId)
  const taskTypes = taskTypesData?.items ?? []

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    setError(null)
    try {
      await create.mutateAsync({
        title: title.trim(),
        priority,
        description: description.trim() || undefined,
        task_type_key: typeKey,
        assignee_id: assigneeId || undefined,
        parent_task_id: parentEpicId || undefined,
      })
      setTitle('')
      setPriority('medium')
      setDescription('')
      setTypeKey('task')
      setAssigneeId('')
      setParentEpicId('')
      onClose()
    } catch (err) {
      const detail = (err as AxiosError<{ detail: unknown }>)?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Something went wrong.')
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) { setError(null); onClose() } }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Create task</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="task-title">Title</Label>
            <Input
              id="task-title"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Task title"
              autoFocus
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="task-type">Type</Label>
              <select
                id="task-type"
                value={typeKey}
                onChange={e => setTypeKey(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {taskTypes.length > 0
                  ? taskTypes.map(t => (
                    <option key={t.key} value={t.key}>{t.name}</option>
                  ))
                  : ['task', 'bug', 'story', 'epic', 'decision'].map(t => (
                    <option key={t} value={t} className="capitalize">{t}</option>
                  ))
                }
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="task-assignee">Assignee</Label>
              <select
                id="task-assignee"
                value={assigneeId}
                onChange={e => setAssigneeId(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">— None —</option>
                {members?.items.map(m => (
                  <option key={m.user.id} value={m.user.id}>{m.user.display_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>Priority</Label>
            <div className="flex gap-1.5">
              {PRIORITIES.map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPriority(p)}
                  className={`flex-1 rounded-md border px-2 py-1.5 text-xs capitalize transition-colors ${
                    priority === p
                      ? 'border-primary bg-primary/10 text-primary font-medium'
                      : 'border-border text-muted-foreground hover:border-ring/50'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {typeKey !== 'epic' && (
            <div className="space-y-1.5">
              <Label htmlFor="task-epic">Epic <span className="text-muted-foreground font-normal">(optional)</span></Label>
              <select
                id="task-epic"
                value={parentEpicId}
                onChange={e => setParentEpicId(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">— No epic —</option>
                {epics.filter(e => !e.deleted_at).map(e => (
                  <option key={e.id} value={e.id}>{e.key}: {e.title}</option>
                ))}
              </select>
              {epics.length === 0 && (
                <p className="text-xs text-muted-foreground">No epics yet — create a task with type "epic" first.</p>
              )}
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="task-desc">
              Description <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <textarea
              id="task-desc"
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Add details…"
              rows={3}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring resize-none"
            />
          </div>

          {error && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={!title.trim() || create.isPending}>
              {create.isPending ? 'Creating…' : 'Create task'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
