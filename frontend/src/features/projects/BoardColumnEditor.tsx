import { useMemo, useState } from 'react'
import { GripVertical, Plus, Trash2, X, AlertTriangle } from 'lucide-react'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import {
  SortableContext, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import {
  useBoardColumns, useCreateBoardColumn, useUpdateBoardColumn, useDeleteBoardColumn,
  useAddStatusToColumn, useRemoveStatusFromColumn,
  useProjectWorkflows,
  type BoardColumn,
} from './workflowApi'

interface Props { viewId: string; projectId: string }

export function BoardColumnEditor({ viewId, projectId }: Props) {
  const { data: boardData, isLoading: bcLoading } = useBoardColumns(viewId)
  const { data: workflows = [], isLoading: wfLoading } = useProjectWorkflows(projectId)
  const createCol = useCreateBoardColumn(viewId)
  const updateCol = useUpdateBoardColumn(viewId)
  const deleteCol = useDeleteBoardColumn(viewId)
  const addStatus = useAddStatusToColumn(viewId)
  const removeStatus = useRemoveStatusFromColumn(viewId)

  const [addingName, setAddingName] = useState('')
  const [addStatusColId, setAddStatusColId] = useState<string | null>(null)

  const sensors = useSensors(useSensor(PointerSensor))

  const columns = useMemo(
    () => [...(boardData?.items ?? [])].sort((a, b) => a.position - b.position),
    [boardData],
  )

  const allStatuses = useMemo(
    () => workflows.flatMap(wf => wf.statuses.map(s => ({ ...s, workflowName: wf.name }))),
    [workflows],
  )

  const mappedStatusIds = useMemo(
    () => new Set(columns.flatMap(c => c.status_ids)),
    [columns],
  )

  const unmappedStatuses = allStatuses.filter(s => !mappedStatusIds.has(s.id))

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIdx = columns.findIndex(c => c.id === active.id)
    const newIdx = columns.findIndex(c => c.id === over.id)
    const reordered = arrayMove(columns, oldIdx, newIdx)
    await Promise.all(
      reordered.map((c, i) =>
        c.position !== i ? updateCol.mutateAsync({ columnId: c.id, position: i }) : Promise.resolve()
      )
    )
  }

  async function handleAddColumn(e: React.FormEvent) {
    e.preventDefault()
    if (!addingName.trim()) return
    await createCol.mutateAsync({ name: addingName.trim(), position: columns.length })
    setAddingName('')
  }

  if (bcLoading || wfLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>
  }

  const statusForCol = addStatusColId ? columns.find(c => c.id === addStatusColId) : null
  const availableForCol = allStatuses.filter(s => !mappedStatusIds.has(s.id))

  // Group by workflow for display
  const byWorkflow = workflows.map(wf => ({
    wf,
    statuses: availableForCol.filter(s => wf.statuses.some(ws => ws.id === s.id)),
  })).filter(g => g.statuses.length > 0)

  return (
    <div className="space-y-3">
      {unmappedStatuses.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 px-3 py-2.5">
          <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" />
          <p className="text-xs text-yellow-800 dark:text-yellow-200">
            <strong>{unmappedStatuses.length}</strong> {unmappedStatuses.length === 1 ? 'status is' : 'statuses are'} not mapped to any column — tasks with these statuses won't appear on the board.
          </p>
        </div>
      )}

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={columns.map(c => c.id)} strategy={verticalListSortingStrategy}>
          <ul className="space-y-2">
            {columns.map(col => (
              <ColumnRow
                key={col.id}
                column={col}
                allStatuses={allStatuses}
                onRename={name => updateCol.mutate({ columnId: col.id, name })}
                onDelete={() => deleteCol.mutate(col.id)}
                onRemoveStatus={statusId => removeStatus.mutate({ columnId: col.id, statusId })}
                onAddStatus={() => setAddStatusColId(col.id)}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>

      {/* Add column form */}
      <form onSubmit={handleAddColumn} className="flex items-center gap-2">
        <Input
          value={addingName}
          onChange={e => setAddingName(e.target.value)}
          placeholder="New column name…"
          className="h-8 text-sm flex-1"
        />
        <Button type="submit" size="sm" className="h-8 gap-1" disabled={!addingName.trim() || createCol.isPending}>
          <Plus className="h-3.5 w-3.5" />
          {createCol.isPending ? 'Adding…' : 'Add column'}
        </Button>
      </form>

      {/* Add status dialog */}
      <Dialog open={!!addStatusColId} onOpenChange={v => !v && setAddStatusColId(null)}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Add status to "{statusForCol?.name}"</DialogTitle>
          </DialogHeader>
          {byWorkflow.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">All statuses are already mapped.</p>
          ) : (
            <div className="space-y-3 max-h-72 overflow-y-auto">
              {byWorkflow.map(({ wf, statuses }) => (
                <div key={wf.id}>
                  <p className="text-xs font-medium text-muted-foreground mb-1.5">{wf.name}</p>
                  <ul className="space-y-1">
                    {statuses.map(s => (
                      <li key={s.id}>
                        <button
                          className="w-full flex items-center gap-2 rounded-md px-3 py-2 text-sm text-left hover:bg-muted transition-colors"
                          onClick={async () => {
                            if (addStatusColId) {
                              await addStatus.mutateAsync({ columnId: addStatusColId, statusId: s.id })
                              setAddStatusColId(null)
                            }
                          }}
                        >
                          <div
                            className="h-2.5 w-2.5 rounded-full shrink-0"
                            style={{ background: s.color ?? 'currentColor' }}
                          />
                          {s.name}
                          <span className="ml-auto text-[10px] text-muted-foreground">{s.category}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

function ColumnRow({
  column, allStatuses, onRename, onDelete, onRemoveStatus, onAddStatus,
}: {
  column: BoardColumn
  allStatuses: { id: string; name: string; color: string | null; workflowName: string }[]
  onRename: (name: string) => void
  onDelete: () => void
  onRemoveStatus: (statusId: string) => void
  onAddStatus: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: column.id })
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(column.name)

  const statusMap = new Map(allStatuses.map(s => [s.id, s]))

  function handleRename() {
    if (name.trim() && name !== column.name) onRename(name.trim())
    setEditing(false)
  }

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        'rounded-lg border bg-background',
        isDragging && 'opacity-50 shadow-lg',
      )}
    >
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button {...attributes} {...listeners} className="cursor-grab text-muted-foreground/40 hover:text-muted-foreground shrink-0">
          <GripVertical className="h-4 w-4" />
        </button>

        {editing ? (
          <Input
            value={name}
            onChange={e => setName(e.target.value)}
            onBlur={handleRename}
            onKeyDown={e => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') { setName(column.name); setEditing(false) } }}
            className="h-6 text-sm flex-1 py-0"
            autoFocus
          />
        ) : (
          <button className="flex-1 text-sm font-medium text-left hover:text-primary" onClick={() => setEditing(true)}>
            {column.name}
          </button>
        )}

        {/* Mapped statuses */}
        <div className="flex items-center gap-1 flex-wrap">
          {column.status_ids.map(sid => {
            const s = statusMap.get(sid)
            if (!s) return null
            return (
              <span
                key={sid}
                className="flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] bg-muted"
              >
                <div className="h-2 w-2 rounded-full" style={{ background: s.color ?? '#888' }} />
                {s.name}
                <button
                  onClick={() => onRemoveStatus(sid)}
                  className="ml-0.5 text-muted-foreground/60 hover:text-destructive"
                >
                  <X className="h-2.5 w-2.5" />
                </button>
              </span>
            )
          })}
          <Button
            size="sm"
            variant="ghost"
            className="h-6 px-2 text-xs text-muted-foreground"
            onClick={onAddStatus}
          >
            <Plus className="h-3 w-3 mr-0.5" />
            Add status
          </Button>
        </div>

        <button
          onClick={onDelete}
          className="rounded p-1 text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0"
          title="Delete column"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </li>
  )
}
