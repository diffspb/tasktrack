import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Kanban, List, Network, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { useProjectByKey } from './api'
import {
  useProjectViews, useCreateView, useUpdateView, useDeleteView,
  type View,
} from './viewsApi'

const VIEW_TYPES: { value: View['type']; label: string; icon: React.ElementType; desc: string }[] = [
  { value: 'kanban',    label: 'Kanban',     icon: Kanban,   desc: 'Columns with drag-and-drop' },
  { value: 'backlog',   label: 'Backlog',    icon: List,     desc: 'Flat task list with filters' },
  { value: 'epic_tree', label: 'Epic tree',  icon: Network,  desc: 'Hierarchical tree by parent' },
]

function TypeBadge({ type }: { type: View['type'] }) {
  const t = VIEW_TYPES.find(x => x.value === type)
  if (!t) return null
  const Icon = t.icon
  return (
    <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium bg-muted text-muted-foreground">
      <Icon className="h-3 w-3" />
      {t.label}
    </span>
  )
}

export function ViewsSettingsPage() {
  const { projectKey } = useParams<{ projectKey: string }>()
  const { data: projectData } = useProjectByKey(projectKey)
  const projectId = projectData?.id

  const { data: views = [] } = useProjectViews(projectId)
  const createView  = useCreateView(projectId)
  const deleteView  = useDeleteView(projectId)

  const [name, setName]     = useState('')
  const [type, setType]     = useState<View['type']>('kanban')
  const [editingId, setEditingId]   = useState<string | null>(null)
  const [editingName, setEditingName] = useState('')

  const updateView = useUpdateView(editingId ?? undefined, projectId)

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await createView.mutateAsync({ name: name.trim(), type })
    setName('')
  }

  async function handleRename(_viewId: string) {
    if (!editingName.trim()) { setEditingId(null); return }
    await updateView.mutateAsync({ name: editingName.trim() })
    setEditingId(null)
  }

  function startEdit(v: View) {
    setEditingId(v.id)
    setEditingName(v.name)
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-7">
      <h1 className="text-xl font-semibold">Views</h1>

      {/* Existing views */}
      <div className="space-y-2">
        {views.map(v => (
          <div key={v.id}
            className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3"
          >
            {editingId === v.id ? (
              <input
                autoFocus
                value={editingName}
                onChange={e => setEditingName(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') handleRename(v.id)
                  if (e.key === 'Escape') setEditingId(null)
                }}
                onBlur={() => handleRename(v.id)}
                className="flex-1 rounded-md border border-primary px-2 py-1 text-sm outline-none"
              />
            ) : (
              <button
                className="flex-1 text-left text-sm font-medium hover:underline decoration-dotted underline-offset-2"
                onClick={() => startEdit(v)}
                title="Click to rename"
              >
                {v.name}
              </button>
            )}

            <TypeBadge type={v.type} />

            {v.is_default && (
              <span className="text-[10px] font-semibold uppercase tracking-wide text-primary/70 bg-primary/10 rounded px-1.5 py-0.5">
                default
              </span>
            )}

            <button
              onClick={() => deleteView.mutateAsync(v.id)}
              disabled={v.is_default || deleteView.isPending}
              title={v.is_default ? 'Cannot delete default view' : 'Delete view'}
              className="rounded p-1.5 text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* Create form */}
      <form onSubmit={handleCreate} className="rounded-lg border p-5 space-y-4">
        <p className="text-sm font-semibold">Add view</p>

        <div className="space-y-1.5">
          <Label htmlFor="view-name" className="text-xs">Name</Label>
          <input
            id="view-name"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g. QA Board"
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary transition-colors"
          />
        </div>

        <div className="space-y-2">
          <Label className="text-xs">Type</Label>
          <div className="grid grid-cols-3 gap-2">
            {VIEW_TYPES.map(t => {
              const Icon = t.icon
              const active = type === t.value
              return (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setType(t.value)}
                  className={`flex flex-col items-center gap-1.5 rounded-lg border-[1.5px] px-3 py-3 text-sm transition-all ${
                    active
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-input text-muted-foreground hover:bg-muted/50'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span className="font-medium text-xs">{t.label}</span>
                  <span className="text-[10px] text-center leading-tight opacity-70">{t.desc}</span>
                </button>
              )
            })}
          </div>
        </div>

        <Button type="submit" size="sm" disabled={!name.trim() || createView.isPending}>
          {createView.isPending ? 'Creating…' : 'Create view'}
        </Button>
      </form>
    </div>
  )
}
