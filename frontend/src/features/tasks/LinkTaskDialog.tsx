import { useState } from 'react'
import { Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { TaskSearchPopover } from '@/shared/ui/TaskSearchPopover'
import { useLinkTypes, useCreateTaskLink, type Task } from './api'
import { TaskTypeIcon, TYPE_COLORS } from './TaskTypeIcon'

type Direction = 'outward' | 'inward'
type ChoiceKey = `${string}:${Direction}`

interface Props {
  open: boolean
  onClose: () => void
  taskId: string
  projectId: string
  excludeIds?: Set<string>
}

export function LinkTaskDialog({ open, onClose, taskId, projectId, excludeIds }: Props) {
  const { data: linkTypes = [] } = useLinkTypes()
  const createLink = useCreateTaskLink(taskId, projectId)

  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [choiceKey, setChoiceKey]       = useState<ChoiceKey | ''>('')

  const activeLinkTypes = linkTypes.filter(lt => lt.is_active)

  // Build flat option list: each directed type yields outward + inward rows;
  // undirected types yield only one row.
  const options = activeLinkTypes.flatMap(lt => {
    const rows: { key: ChoiceKey; label: string; color: string }[] = [
      { key: `${lt.id}:outward`, label: lt.outward_name, color: lt.color ?? '#6366f1' },
    ]
    if (lt.is_directed) {
      rows.push({ key: `${lt.id}:inward`, label: lt.inward_name, color: lt.color ?? '#6366f1' })
    }
    return rows
  })

  const selectedOpt = options.find(o => o.key === choiceKey)

  async function handleSubmit() {
    if (!selectedTask || !choiceKey) return
    const [linkTypeId, dir] = choiceKey.split(':') as [string, Direction]
    await createLink.mutateAsync(
      dir === 'outward'
        ? { source_task_id: taskId,          target_task_id: selectedTask.id, link_type_id: linkTypeId }
        : { source_task_id: selectedTask.id, target_task_id: taskId,          link_type_id: linkTypeId },
    )
    resetAndClose()
  }

  function resetAndClose() {
    setSelectedTask(null)
    setChoiceKey('')
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && resetAndClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Link task</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-1">
          {/* Link type + direction — dropdown */}
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Link type</p>
            <select
              value={choiceKey}
              onChange={e => setChoiceKey(e.target.value as ChoiceKey | '')}
              className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring text-foreground"
            >
              <option value="">Select link type…</option>
              {options.map(opt => (
                <option key={opt.key} value={opt.key}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Target task picker */}
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">
              {selectedOpt ? `"${selectedOpt.label}"` : 'Task'}
            </p>
            {selectedTask ? (
              <div className="flex items-center gap-2 rounded-lg border px-3 py-2 bg-muted/20">
                <TaskTypeIcon
                  typeKey={selectedTask.task_type?.key ?? 'task'}
                  color={selectedTask.task_type?.color ?? TYPE_COLORS[selectedTask.task_type?.key ?? 'task'] ?? '#6366f1'}
                  size={13}
                />
                <span className="font-mono text-[11px] text-muted-foreground">{selectedTask.key}</span>
                <span className="text-sm flex-1 truncate">{selectedTask.title}</span>
                <button
                  onClick={() => setSelectedTask(null)}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Change
                </button>
              </div>
            ) : (
              <TaskSearchPopover
                excludeIds={excludeIds}
                onSelect={setSelectedTask}
                trigger={
                  <button className="w-full flex items-center gap-2 rounded-lg border px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors text-left">
                    <Link2 className="h-3.5 w-3.5 shrink-0" />
                    Search task by key or title…
                  </button>
                }
              />
            )}
          </div>

          {/* Preview */}
          {selectedTask && selectedOpt && (
            <p className="text-xs text-muted-foreground bg-muted/30 rounded px-3 py-2">
              This task{' '}
              <span className="font-medium text-foreground">{selectedOpt.label}</span>{' '}
              <span className="font-mono">{selectedTask.key}</span>
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" onClick={resetAndClose}>Cancel</Button>
            <Button
              size="sm"
              disabled={!selectedTask || !choiceKey || createLink.isPending}
              onClick={handleSubmit}
            >
              Add link
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
