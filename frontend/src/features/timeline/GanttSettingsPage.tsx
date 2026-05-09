import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useGanttChart, useUpdateGanttChart, useDeleteGanttChart } from './ganttApi'

export function GanttSettingsPage() {
  const { ganttId } = useParams<{ ganttId: string }>()
  const navigate = useNavigate()

  const { data: gantt, isLoading } = useGanttChart(ganttId)
  const updateMutation = useUpdateGanttChart(ganttId!)
  const deleteMutation = useDeleteGanttChart()

  const [name, setName]             = useState('')
  const [description, setDescription] = useState('')
  const [dirty, setDirty]           = useState(false)

  if (isLoading) return <div className="p-8 text-sm text-muted-foreground">Loading…</div>
  if (!gantt) return null

  const currentName = dirty ? name : gantt.name
  const currentDesc = dirty ? description : (gantt.description ?? '')

  async function handleSave() {
    await updateMutation.mutateAsync({
      name: currentName,
      description: currentDesc || undefined,
    })
    setDirty(false)
  }

  async function handleDelete() {
    if (!confirm(`Delete timeline "${gantt!.name}"? This cannot be undone.`)) return
    await deleteMutation.mutateAsync(gantt!.id)
    navigate('/timeline')
  }

  return (
    <div className="max-w-lg mx-auto px-6 py-8 space-y-8">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => navigate(`/timeline/${ganttId}`)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-base font-semibold">Timeline settings</h1>
      </div>

      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Name</label>
          <Input
            value={currentName}
            onChange={e => { setName(e.target.value); setDirty(true) }}
            className="max-w-sm"
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Description</label>
          <Input
            value={currentDesc}
            onChange={e => { setDescription(e.target.value); setDirty(true) }}
            placeholder="Optional description"
            className="max-w-sm"
          />
        </div>
        <Button onClick={handleSave} disabled={updateMutation.isPending}>
          Save changes
        </Button>
      </div>

      <div className="border-t pt-6 space-y-2">
        <p className="text-sm font-medium text-destructive">Danger zone</p>
        <p className="text-xs text-muted-foreground">Deleting the timeline removes it permanently. Tasks are not affected.</p>
        <Button variant="destructive" size="sm" onClick={handleDelete} disabled={deleteMutation.isPending}>
          Delete timeline
        </Button>
      </div>
    </div>
  )
}
