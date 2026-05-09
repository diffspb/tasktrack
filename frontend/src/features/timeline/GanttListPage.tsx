import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, CalendarRange, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useGanttCharts, useCreateGanttChart, useDeleteGanttChart } from './ganttApi'

export function GanttListPage() {
  const navigate = useNavigate()
  const { data: charts = [], isLoading } = useGanttCharts()
  const createMutation = useCreateGanttChart()
  const deleteMutation = useDeleteGanttChart()

  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')

  async function handleCreate() {
    if (!newName.trim()) return
    const chart = await createMutation.mutateAsync({ name: newName.trim() })
    setNewName('')
    setCreating(false)
    navigate(`/timeline/${chart.id}`)
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <CalendarRange className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold">All timelines</h1>
        <Button
          variant="outline" size="sm" className="ml-auto gap-1.5"
          onClick={() => setCreating(true)}
        >
          <Plus className="h-3.5 w-3.5" /> New timeline
        </Button>
      </div>

      {creating && (
        <div className="flex gap-2">
          <Input
            autoFocus
            placeholder="Timeline name"
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') handleCreate()
              if (e.key === 'Escape') setCreating(false)
            }}
            className="h-8 text-sm"
          />
          <Button size="sm" disabled={createMutation.isPending || !newName.trim()} onClick={handleCreate}>
            Create
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setCreating(false)}>Cancel</Button>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : charts.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-48 text-center gap-3">
          <CalendarRange className="h-10 w-10 text-muted-foreground/30" />
          <p className="text-sm text-muted-foreground">No timelines yet.</p>
          <Button variant="outline" size="sm" onClick={() => setCreating(true)}>
            Create your first timeline
          </Button>
        </div>
      ) : (
        <div className="divide-y rounded-lg border overflow-hidden">
          {charts.map(chart => (
            <div
              key={chart.id}
              className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 cursor-pointer group"
              onClick={() => navigate(`/timeline/${chart.id}`)}
            >
              <CalendarRange className="h-4 w-4 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{chart.name}</p>
                {chart.description && (
                  <p className="text-xs text-muted-foreground truncate">{chart.description}</p>
                )}
              </div>
              <Button
                size="sm" variant="ghost"
                className="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive"
                onClick={e => {
                  e.stopPropagation()
                  if (confirm(`Delete "${chart.name}"?`)) deleteMutation.mutate(chart.id)
                }}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
