import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Plus, Pencil, Trash2, Check, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useLinkTypes, useCreateLinkType, useUpdateLinkType, useDeleteLinkType,
  type LinkType, type LinkTypeUpdate,
} from './api'

// ── Constraint presets ────────────────────────────────────────────────────────

const PRESETS = [
  { label: 'None',                                      value: null },
  { label: 'Blocking (source can\'t close until target closes)', value: { type: 'blocking' } },
  { label: 'Sequential / Finish-to-Start (Gantt)',      value: { type: 'sequential', mode: 'finish_to_start' } },
]

function constraintLabel(c: Record<string, unknown> | null) {
  if (!c) return '—'
  if (c.type === 'blocking') return 'Blocking'
  if (c.type === 'sequential') return `Sequential (${c.mode ?? 'FS'})`
  return JSON.stringify(c)
}

function presetIndex(c: Record<string, unknown> | null) {
  return PRESETS.findIndex(p => JSON.stringify(p.value) === JSON.stringify(c))
}

// ── Edit row ──────────────────────────────────────────────────────────────────

function EditRowWrapper({ lt, onClose }: { lt: LinkType; onClose: () => void }) {
  const update = useUpdateLinkType(lt.id)
  const [form, setForm] = useState({
    outward_name: lt.outward_name,
    inward_name:  lt.inward_name,
    is_directed:  lt.is_directed,
    color:        lt.color ?? '#6366f1',
    constraint:   lt.constraint,
  })

  async function save() {
    const data: LinkTypeUpdate = {
      outward_name: form.outward_name,
      inward_name:  form.is_directed ? form.inward_name : form.outward_name,
      is_directed:  form.is_directed,
      color:        form.color || null,
      constraint:   form.constraint,
    }
    await update.mutateAsync(data)
    onClose()
  }

  const idx = presetIndex(form.constraint)

  return (
    <tr className="bg-muted/30">
      <td className="px-4 py-2 font-mono text-xs">{lt.name}</td>
      <td className="px-4 py-2">
        <Input value={form.outward_name} onChange={e => setForm(s => ({ ...s, outward_name: e.target.value }))} className="h-7 text-sm" />
      </td>
      <td className="px-4 py-2">
        <Input value={form.inward_name} onChange={e => setForm(s => ({ ...s, inward_name: e.target.value }))} className="h-7 text-sm" disabled={!form.is_directed} placeholder={form.is_directed ? '' : '(same as outward)'} />
      </td>
      <td className="px-4 py-2 text-center">
        <input type="checkbox" checked={form.is_directed} onChange={e => setForm(s => ({ ...s, is_directed: e.target.checked }))} />
      </td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-2">
          <input type="color" value={form.color} onChange={e => setForm(s => ({ ...s, color: e.target.value }))} className="h-7 w-9 rounded border cursor-pointer" />
          <span className="text-xs text-muted-foreground">{form.color}</span>
        </div>
      </td>
      <td className="px-4 py-2">
        <select className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
          value={idx >= 0 ? idx : 0}
          onChange={e => setForm(s => ({ ...s, constraint: PRESETS[Number(e.target.value)]?.value ?? null }))}>
          {PRESETS.map((p, i) => <option key={i} value={i}>{p.label}</option>)}
        </select>
      </td>
      <td className="px-4 py-2">
        <div className="flex gap-1">
          <Button size="sm" className="h-7 px-2" disabled={update.isPending} onClick={save}><Check className="h-3.5 w-3.5" /></Button>
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onClose}><X className="h-3.5 w-3.5" /></Button>
        </div>
      </td>
    </tr>
  )
}

// ── Create row ────────────────────────────────────────────────────────────────

function CreateRow({ onClose }: { onClose: () => void }) {
  const create = useCreateLinkType()
  const [form, setForm] = useState({ name: '', outward_name: '', inward_name: '', is_directed: true, color: '#6366f1', constraint: null as Record<string, unknown> | null })
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    if (!form.name.trim() || !form.outward_name.trim()) return
    setError(null)
    try {
      await create.mutateAsync({
        name: form.name.trim(),
        outward_name: form.outward_name.trim(),
        inward_name: form.is_directed ? form.inward_name.trim() : form.outward_name.trim(),
        is_directed: form.is_directed,
        color: form.color || null,
        constraint: form.constraint,
      })
      onClose()
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      setError(code === 'DUPLICATE_LINK_TYPE_NAME' ? 'Name already exists.' : 'Failed to create.')
    }
  }

  return (
    <tr className="bg-primary/5 border-t">
      <td className="px-4 py-2">
        <Input value={form.name} onChange={e => setForm(s => ({ ...s, name: e.target.value }))} placeholder="e.g. relates_to" className="h-7 text-sm font-mono" autoFocus />
      </td>
      <td className="px-4 py-2">
        <Input value={form.outward_name} onChange={e => setForm(s => ({ ...s, outward_name: e.target.value }))} placeholder="relates to" className="h-7 text-sm" />
      </td>
      <td className="px-4 py-2">
        <Input value={form.inward_name} onChange={e => setForm(s => ({ ...s, inward_name: e.target.value }))} placeholder="relates to" className="h-7 text-sm" disabled={!form.is_directed} />
      </td>
      <td className="px-4 py-2 text-center">
        <input type="checkbox" checked={form.is_directed} onChange={e => setForm(s => ({ ...s, is_directed: e.target.checked }))} />
      </td>
      <td className="px-4 py-2">
        <input type="color" value={form.color} onChange={e => setForm(s => ({ ...s, color: e.target.value }))} className="h-7 w-9 rounded border cursor-pointer" />
      </td>
      <td className="px-4 py-2">
        <select className="w-full rounded border border-input bg-background px-2 py-1 text-xs"
          value={presetIndex(form.constraint)}
          onChange={e => setForm(s => ({ ...s, constraint: PRESETS[Number(e.target.value)]?.value ?? null }))}>
          {PRESETS.map((p, i) => <option key={i} value={i}>{p.label}</option>)}
        </select>
      </td>
      <td className="px-4 py-2">
        <div className="flex gap-1">
          <Button size="sm" className="h-7 px-2" disabled={create.isPending} onClick={submit}><Check className="h-3.5 w-3.5" /></Button>
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onClose}><X className="h-3.5 w-3.5" /></Button>
        </div>
        {error && <p className="text-xs text-destructive mt-1">{error}</p>}
      </td>
    </tr>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function LinkTypesSettingsPage() {
  const { data: linkTypes = [], isLoading } = useLinkTypes(true)
  const deleteMutation = useDeleteLinkType()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold">Link types</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Define how tasks can be connected across projects. Directed links have different outward / inward names.
          Constraints enforce business rules such as blocking or Gantt-style finish-to-start dependencies.
        </p>
      </div>

      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-2 text-left font-semibold w-32">Name</th>
              <th className="px-4 py-2 text-left font-semibold">Outward</th>
              <th className="px-4 py-2 text-left font-semibold">Inward</th>
              <th className="px-4 py-2 text-center font-semibold w-20">Directed</th>
              <th className="px-4 py-2 text-left font-semibold w-32">Color</th>
              <th className="px-4 py-2 text-left font-semibold">Constraint</th>
              <th className="px-4 py-2 w-24" />
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-sm text-muted-foreground">Loading…</td></tr>
            ) : linkTypes.map(lt =>
              editingId === lt.id ? (
                <EditRowWrapper key={lt.id} lt={lt} onClose={() => setEditingId(null)} />
              ) : (
                <tr key={lt.id} className={!lt.is_active ? 'opacity-50' : undefined}>
                  <td className="px-4 py-2.5 font-mono text-xs">{lt.name}</td>
                  <td className="px-4 py-2.5">{lt.outward_name}</td>
                  <td className="px-4 py-2.5 text-muted-foreground">
                    {lt.is_directed ? lt.inward_name : <span className="italic">symmetric</span>}
                  </td>
                  <td className="px-4 py-2.5 text-center text-base">{lt.is_directed ? '→' : '↔'}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      {lt.color && <div className="h-4 w-4 rounded-sm shrink-0" style={{ background: lt.color }} />}
                      <span className="text-xs text-muted-foreground">{lt.color ?? '—'}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-muted-foreground">{constraintLabel(lt.constraint)}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-1 justify-end">
                      <Button size="sm" variant="ghost" className="h-7 px-2" onClick={() => { setCreating(false); setEditingId(lt.id) }}>
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <Button size="sm" variant="ghost" className="h-7 px-2 text-destructive hover:text-destructive"
                        disabled={deleteMutation.isPending}
                        onClick={async () => {
                          if (confirm(`Delete link type "${lt.name}"?`))
                            await deleteMutation.mutateAsync(lt.id)
                        }}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </td>
                </tr>
              )
            )}
            {creating && <CreateRow onClose={() => setCreating(false)} />}
          </tbody>
        </table>
      </div>

      {!creating && !editingId && (
        <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setCreating(true)}>
          <Plus className="h-3.5 w-3.5" /> Add link type
        </Button>
      )}
    </div>
  )
}
