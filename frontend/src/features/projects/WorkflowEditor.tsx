import { useState } from 'react'
import { GripVertical, Plus, Trash2, ArrowRight, X } from 'lucide-react'
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
  useProjectWorkflows, useCreateStatus, useUpdateStatus, useDeleteStatus,
  useMigrateStatus, useCreateTransition, useDeleteTransition,
  useCreateWorkflow, useUpdateWorkflow, useDeleteWorkflow,
  type Workflow, type WorkflowStatus, type StatusCategory,
} from './workflowApi'

const CATEGORY_OPTS: { value: StatusCategory; label: string; cls: string }[] = [
  { value: 'initial',      label: 'Initial',       cls: 'bg-muted text-muted-foreground' },
  { value: 'intermediate', label: 'Intermediate',   cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  { value: 'final',        label: 'Final',          cls: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' },
]

const DEFAULT_COLORS = ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#64748b']

interface Props { projectId: string }

export function WorkflowEditor({ projectId }: Props) {
  const { data: workflows = [], isLoading } = useProjectWorkflows(projectId)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  const createWorkflow = useCreateWorkflow(projectId)
  const updateWorkflow = useUpdateWorkflow(projectId)
  const deleteWorkflow = useDeleteWorkflow(projectId)

  const selected = (selectedId ? workflows.find(w => w.id === selectedId) : null)
    ?? workflows.find(w => w.is_default)
    ?? workflows[0]

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading workflow…</p>
  if (!selected) return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">No workflows yet.</p>
      <Button size="sm" variant="outline" className="gap-1" onClick={() => setCreateOpen(true)}>
        <Plus className="h-3.5 w-3.5" /> New workflow
      </Button>
      <CreateWorkflowDialog
        open={createOpen}
        isPending={createWorkflow.isPending}
        onConfirm={async name => {
          const wf = await createWorkflow.mutateAsync(name)
          setSelectedId(wf.id)
          setCreateOpen(false)
        }}
        onCancel={() => setCreateOpen(false)}
      />
    </div>
  )

  const deleteTarget = workflows.find(w => w.id === deleteConfirmId)

  return (
    <div className="space-y-6">
      {/* Workflow tab bar */}
      <div className="flex items-center gap-0 border-b">
        {workflows.length > 1
          ? workflows.map(wf => (
            <div key={wf.id} className="flex items-center">
              <button
                onClick={() => setSelectedId(wf.id)}
                className={cn(
                  'flex items-center gap-1.5 px-3 py-2 text-sm border-b-2 -mb-px transition-colors',
                  wf.id === selected.id
                    ? 'border-primary text-foreground font-medium'
                    : 'border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                {wf.name}
                {wf.is_default
                  ? <span className="text-[10px] text-muted-foreground">(default)</span>
                  : (
                    <button
                      onClick={e => { e.stopPropagation(); updateWorkflow.mutate({ workflowId: wf.id, is_default: true }) }}
                      className="text-[10px] text-muted-foreground/50 hover:text-primary underline underline-offset-2"
                      title="Set as default workflow for new tasks"
                    >
                      set default
                    </button>
                  )
                }
              </button>
              <button
                onClick={() => setDeleteConfirmId(wf.id)}
                className="rounded p-0.5 text-muted-foreground/40 hover:text-destructive transition-colors -ml-1 mr-1"
                title="Delete workflow"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))
          : (
            <span className="px-1 py-2 text-sm font-medium text-foreground">
              {selected.name}
              {selected.is_default && (
                <span className="ml-1 text-[10px] text-muted-foreground">(default)</span>
              )}
            </span>
          )
        }
        <Button
          size="sm"
          variant="ghost"
          className="ml-auto h-8 gap-1 text-xs text-muted-foreground hover:text-foreground"
          onClick={() => setCreateOpen(true)}
        >
          <Plus className="h-3.5 w-3.5" /> New workflow
        </Button>
      </div>

      <StatusesEditor workflow={selected} projectId={projectId} />
      <TransitionsEditor workflow={selected} projectId={projectId} />

      <CreateWorkflowDialog
        open={createOpen}
        isPending={createWorkflow.isPending}
        onConfirm={async name => {
          const wf = await createWorkflow.mutateAsync(name)
          setSelectedId(wf.id)
          setCreateOpen(false)
        }}
        onCancel={() => setCreateOpen(false)}
      />

      {deleteTarget && (
        <DeleteWorkflowDialog
          workflow={deleteTarget}
          isPending={deleteWorkflow.isPending}
          onConfirm={async () => {
            await deleteWorkflow.mutateAsync(deleteTarget.id)
            if (selected.id === deleteTarget.id) setSelectedId(null)
            setDeleteConfirmId(null)
          }}
          onCancel={() => setDeleteConfirmId(null)}
        />
      )}
    </div>
  )
}

function CreateWorkflowDialog({
  open, isPending, onConfirm, onCancel,
}: {
  open: boolean
  isPending: boolean
  onConfirm: (name: string) => Promise<void>
  onCancel: () => void
}) {
  const [name, setName] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await onConfirm(name.trim())
    setName('')
  }

  return (
    <Dialog open={open} onOpenChange={v => !v && onCancel()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>New workflow</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <Input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Workflow name"
            autoFocus
          />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
            <Button type="submit" size="sm" disabled={!name.trim() || isPending}>
              {isPending ? 'Creating…' : 'Create'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DeleteWorkflowDialog({
  workflow, isPending, onConfirm, onCancel,
}: {
  workflow: Workflow
  isPending: boolean
  onConfirm: () => Promise<void>
  onCancel: () => void
}) {
  return (
    <Dialog open onOpenChange={v => !v && onCancel()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Delete workflow</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Delete <strong>{workflow.name}</strong>? Tasks using this workflow will block deletion.
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel}>Cancel</Button>
          <Button variant="destructive" size="sm" disabled={isPending} onClick={onConfirm}>
            {isPending ? 'Deleting…' : 'Delete'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── Statuses ──────────────────────────────────────────────────────────────────

function StatusesEditor({ workflow, projectId }: { workflow: Workflow; projectId: string }) {
  const [statuses, setStatuses] = useState<WorkflowStatus[]>(() =>
    [...workflow.statuses].sort((a, b) => a.position - b.position)
  )
  const [addOpen, setAddOpen] = useState(false)
  const [migrateFor, setMigrateFor] = useState<WorkflowStatus | null>(null)

  const updateStatus = useUpdateStatus(projectId)
  const deleteStatus = useDeleteStatus(projectId)
  const migrateStatus = useMigrateStatus(projectId)

  // Keep local statuses in sync when workflow refetches
  if (workflow.statuses.length !== statuses.length ||
      workflow.statuses.some(s => !statuses.find(ls => ls.id === s.id))) {
    setStatuses([...workflow.statuses].sort((a, b) => a.position - b.position))
  }

  const sensors = useSensors(useSensor(PointerSensor))

  async function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIndex = statuses.findIndex(s => s.id === active.id)
    const newIndex = statuses.findIndex(s => s.id === over.id)
    const reordered = arrayMove(statuses, oldIndex, newIndex)
    setStatuses(reordered)
    // Persist new positions
    await Promise.all(
      reordered.map((s, i) =>
        s.position !== i ? updateStatus.mutateAsync({ statusId: s.id, position: i }) : Promise.resolve()
      )
    )
  }

  async function handleDelete(status: WorkflowStatus) {
    try {
      await deleteStatus.mutateAsync(status.id)
      setStatuses(prev => prev.filter(s => s.id !== status.id))
    } catch (err: unknown) {
      const code = (err as { response?: { data?: { detail?: { code?: string } } } })
        ?.response?.data?.detail?.code
      if (code === 'STATUS_HAS_ACTIVE_TASKS') {
        setMigrateFor(status)
      }
    }
  }

  const otherStatuses = statuses.filter(s => s.id !== migrateFor?.id)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Statuses</h3>
        <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => setAddOpen(true)}>
          <Plus className="h-3.5 w-3.5" /> Add status
        </Button>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={statuses.map(s => s.id)} strategy={verticalListSortingStrategy}>
          <ul className="space-y-1.5">
            {statuses.map(status => (
              <SortableStatusRow
                key={status.id}
                status={status}
                projectId={projectId}
                onDelete={() => handleDelete(status)}
              />
            ))}
          </ul>
        </SortableContext>
      </DndContext>

      {addOpen && (
        <AddStatusForm
          workflowId={workflow.id}
          projectId={projectId}
          nextPosition={statuses.length}
          onDone={() => setAddOpen(false)}
        />
      )}

      {/* Migrate dialog */}
      {migrateFor && (
        <MigrateDialog
          status={migrateFor}
          targets={otherStatuses}
          onConfirm={async targetId => {
            await migrateStatus.mutateAsync({ statusId: migrateFor.id, targetStatusId: targetId })
            setStatuses(prev => prev.filter(s => s.id !== migrateFor.id))
            setMigrateFor(null)
          }}
          onCancel={() => setMigrateFor(null)}
        />
      )}
    </div>
  )
}

function SortableStatusRow({
  status, projectId, onDelete,
}: {
  status: WorkflowStatus; projectId: string; onDelete: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: status.id })
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(status.name)
  const [color, setColor] = useState(status.color ?? '#6366f1')
  const [category, setCategory] = useState<StatusCategory>(status.category)
  const [isDefault, setIsDefault] = useState(status.is_default)
  const updateStatus = useUpdateStatus(projectId)

  const catMeta = CATEGORY_OPTS.find(c => c.value === status.category)

  async function saveEdit() {
    const changes: Record<string, unknown> = { statusId: status.id }
    if (name.trim() !== status.name) changes.name = name.trim()
    if (color !== status.color) changes.color = color
    if (category !== status.category) changes.category = category
    if (isDefault !== status.is_default) changes.is_default = isDefault
    if (Object.keys(changes).length > 1) {
      await updateStatus.mutateAsync(changes as Parameters<typeof updateStatus.mutateAsync>[0])
    }
    setEditing(false)
  }

  function cancelEdit() {
    setName(status.name)
    setColor(status.color ?? '#6366f1')
    setCategory(status.category)
    setIsDefault(status.is_default)
    setEditing(false)
  }

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn('rounded-lg border bg-background px-3 py-2',
        isDragging && 'opacity-50 shadow-lg')}
    >
      {editing ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <button {...attributes} {...listeners} className="cursor-grab text-muted-foreground/40 shrink-0">
              <GripVertical className="h-4 w-4" />
            </button>
            <div className="h-3 w-3 rounded-full shrink-0 border" style={{ background: color }} />
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') saveEdit(); if (e.key === 'Escape') cancelEdit() }}
              className="h-7 text-xs flex-1"
              autoFocus
            />
            <select
              value={category}
              onChange={e => {
                const v = e.target.value as StatusCategory
                setCategory(v)
                if (v !== 'initial') setIsDefault(false)
              }}
              className="h-7 rounded-md border border-input bg-background px-2 text-xs"
            >
              {CATEGORY_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div className="flex items-center gap-2 pl-9">
            <span className="text-xs text-muted-foreground">Color:</span>
            {DEFAULT_COLORS.map(c => (
              <button key={c} type="button" onClick={() => setColor(c)}
                className={cn('h-5 w-5 rounded-full border-2 transition-all',
                  color === c ? 'border-foreground scale-110' : 'border-transparent')}
                style={{ background: c }}
              />
            ))}
            {category === 'initial' && (
              <label className="ml-2 flex items-center gap-1.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={isDefault}
                  onChange={e => setIsDefault(e.target.checked)}
                  className="rounded"
                />
                <span className="text-xs text-muted-foreground">Default</span>
              </label>
            )}
            <div className="flex-1" />
            <Button size="sm" className="h-6 px-2 text-xs" onClick={saveEdit} disabled={updateStatus.isPending}>
              {updateStatus.isPending ? 'Saving…' : 'Save'}
            </Button>
            <Button size="sm" variant="ghost" className="h-6 px-2 text-xs" onClick={cancelEdit}>Cancel</Button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <button {...attributes} {...listeners} className="cursor-grab text-muted-foreground/40 hover:text-muted-foreground shrink-0">
            <GripVertical className="h-4 w-4" />
          </button>
          <div className="h-3 w-3 rounded-full shrink-0 border" style={{ background: status.color ?? '#6366f1' }} />
          <button className="flex-1 text-sm text-left hover:text-primary transition-colors" onClick={() => setEditing(true)}>
            {status.name}
          </button>
          <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-medium shrink-0', catMeta?.cls)}>
            {catMeta?.label}
          </span>
          {status.is_default && (
            <span className="text-[10px] text-muted-foreground bg-muted rounded px-1.5 py-0.5 shrink-0">default</span>
          )}
          <button onClick={onDelete} className="rounded p-1 text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </li>
  )
}

function AddStatusForm({ workflowId, projectId, nextPosition, onDone }: {
  workflowId: string; projectId: string; nextPosition: number; onDone: () => void
}) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState<StatusCategory>('intermediate')
  const [color, setColor] = useState('#6366f1')
  const [isDefault, setIsDefault] = useState(false)
  const createStatus = useCreateStatus(projectId)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await createStatus.mutateAsync({
      workflowId, name: name.trim(), category,
      position: nextPosition, color, is_default: isDefault,
    })
    onDone()
  }

  return (
    <form onSubmit={handleSubmit} className="rounded-lg border border-dashed p-3 space-y-3">
      <div className="flex items-center gap-2">
        <Input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder="Status name"
          className="h-7 text-xs flex-1"
          autoFocus
        />
        <select
          value={category}
          onChange={e => {
            const v = e.target.value as StatusCategory
            setCategory(v)
            if (v !== 'initial') setIsDefault(false)
          }}
          className="h-7 rounded-md border border-input bg-background px-2 text-xs"
        >
          {CATEGORY_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Color:</span>
        {DEFAULT_COLORS.map(c => (
          <button key={c} type="button" onClick={() => setColor(c)}
            className={cn('h-5 w-5 rounded-full border-2 transition-all',
              color === c ? 'border-foreground scale-110' : 'border-transparent')}
            style={{ background: c }}
          />
        ))}
        {category === 'initial' && (
          <label className="ml-2 flex items-center gap-1.5 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={e => setIsDefault(e.target.checked)}
              className="rounded"
            />
            <span className="text-xs text-muted-foreground">Default</span>
          </label>
        )}
        <div className="flex-1" />
        <Button type="button" variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onDone}>Cancel</Button>
        <Button type="submit" size="sm" className="h-6 px-2 text-xs" disabled={!name.trim() || createStatus.isPending}>
          {createStatus.isPending ? 'Adding…' : 'Add'}
        </Button>
      </div>
    </form>
  )
}

function MigrateDialog({ status, targets, onConfirm, onCancel }: {
  status: WorkflowStatus
  targets: WorkflowStatus[]
  onConfirm: (targetId: string) => Promise<void>
  onCancel: () => void
}) {
  const [targetId, setTargetId] = useState(targets[0]?.id ?? '')
  const [pending, setPending] = useState(false)

  async function handleConfirm() {
    if (!targetId) return
    setPending(true)
    await onConfirm(targetId)
    setPending(false)
  }

  return (
    <div className="rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20 p-4 space-y-3">
      <p className="text-sm font-medium">
        Status <strong>{status.name}</strong> has active tasks.
      </p>
      <p className="text-xs text-muted-foreground">
        Move all tasks to another status before deleting:
      </p>
      <select
        value={targetId}
        onChange={e => setTargetId(e.target.value)}
        className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm"
      >
        {targets.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button size="sm" disabled={!targetId || pending} onClick={handleConfirm}>
          {pending ? 'Migrating…' : 'Migrate & delete'}
        </Button>
      </div>
    </div>
  )
}

// ── Transitions ───────────────────────────────────────────────────────────────

function TransitionsEditor({ workflow, projectId }: { workflow: Workflow; projectId: string }) {
  const [addOpen, setAddOpen] = useState(false)
  const [fromId, setFromId] = useState('')
  const [toId, setToId] = useState('')
  const createTransition = useCreateTransition(projectId)
  const deleteTransition = useDeleteTransition(projectId)

  const statuses = [...workflow.statuses].sort((a, b) => a.position - b.position)
  const statusById = new Map(statuses.map(s => [s.id, s]))

  const existingPairs = new Set(workflow.transitions.map(t => `${t.from_status_id}→${t.to_status_id}`))

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!fromId || !toId || fromId === toId) return
    if (existingPairs.has(`${fromId}→${toId}`)) return
    await createTransition.mutateAsync({ workflowId: workflow.id, from_status_id: fromId, to_status_id: toId })
    setAddOpen(false); setFromId(''); setToId('')
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Transitions</h3>
        <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => setAddOpen(true)}>
          <Plus className="h-3.5 w-3.5" /> Add transition
        </Button>
      </div>

      {workflow.transitions.length === 0 && !addOpen && (
        <p className="text-xs text-muted-foreground">No transitions — tasks won't be movable on the board.</p>
      )}

      <ul className="space-y-1.5">
        {workflow.transitions.map(t => {
          const from = statusById.get(t.from_status_id)
          const to = statusById.get(t.to_status_id)
          if (!from || !to) return null
          return (
            <li key={t.id} className="flex items-center gap-2.5 rounded-lg border bg-background px-3 py-2">
              <span className="text-sm font-medium w-32 truncate">{from.name}</span>
              <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />
              <span className="text-sm font-medium flex-1 truncate">{to.name}</span>
              <button
                onClick={() => deleteTransition.mutateAsync(t.id)}
                className="rounded p-1 text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          )
        })}
      </ul>

      {addOpen && (
        <form onSubmit={handleAdd} className="rounded-lg border border-dashed p-3 space-y-2">
          <div className="flex items-center gap-2">
            <select value={fromId} onChange={e => setFromId(e.target.value)}
              className="flex-1 h-7 rounded-md border border-input bg-background px-2 text-xs">
              <option value="">From…</option>
              {statuses.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />
            <select value={toId} onChange={e => setToId(e.target.value)}
              className="flex-1 h-7 rounded-md border border-input bg-background px-2 text-xs">
              <option value="">To…</option>
              {statuses.filter(s => s.id !== fromId).map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button type="submit" size="sm" className="h-6 px-2 text-xs"
              disabled={!fromId || !toId || fromId === toId || createTransition.isPending}>
              {createTransition.isPending ? 'Adding…' : 'Add'}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
