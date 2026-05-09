import { useState } from 'react'
import { Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { TaskSearchPopover } from '@/shared/ui/TaskSearchPopover'
import { useLinkTypes, useCreateTaskLink, type Task, type TaskLinkTask } from './api'
import { TaskTypeIcon, TYPE_COLORS } from './TaskTypeIcon'

interface Props {
  open: boolean
  onClose: () => void
  taskId: string
  /** Exclude the task itself and already-linked tasks from search */
  excludeIds?: Set<string>
}

export function LinkTaskDialog({ open, onClose, taskId, excludeIds }: Props) {
  const { data: linkTypes = [] } = useLinkTypes()
  const createLink = useCreateTaskLink(taskId)

  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [linkTypeId, setLinkTypeId] = useState<string>('')

  const activeLinkTypes = linkTypes.filter(lt => lt.is_active)

  async function handleSubmit() {
    if (!selectedTask || !linkTypeId) return
    await createLink.mutateAsync({ target_task_id: selectedTask.id, link_type_id: linkTypeId })
    setSelectedTask(null)
    setLinkTypeId('')
    onClose()
  }

  function handleClose() {
    setSelectedTask(null)
    setLinkTypeId('')
    onClose()
  }

  const selectedType = activeLinkTypes.find(lt => lt.id === linkTypeId)

  return (
    <Dialog open={open} onOpenChange={v => !v && handleClose()}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Link task</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 pt-1">
          {/* Link type selector */}
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Link type</p>
            <div className="flex flex-wrap gap-1.5">
              {activeLinkTypes.map(lt => (
                <button
                  key={lt.id}
                  onClick={() => setLinkTypeId(lt.id)}
                  className="flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium border transition-colors"
                  style={
                    linkTypeId === lt.id
                      ? { background: lt.color ?? '#6366f1', color: '#fff', borderColor: 'transparent' }
                      : { borderColor: 'var(--border)', color: 'var(--muted-foreground)' }
                  }
                >
                  <Link2 className="h-3 w-3" />
                  {lt.outward_name}
                </button>
              ))}
            </div>
          </div>

          {/* Target task picker */}
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">
              {selectedType ? `Task to "${selectedType.outward_name}"` : 'Target task'}
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

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-1">
            <Button variant="ghost" size="sm" onClick={handleClose}>Cancel</Button>
            <Button
              size="sm"
              disabled={!selectedTask || !linkTypeId || createLink.isPending}
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
