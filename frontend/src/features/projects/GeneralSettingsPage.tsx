import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Download, Globe, Users, Lock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import { useProjectByKey, useUpdateProject, useArchiveProject, downloadProjectExport } from './api'
import type { Project } from './api'

type Visibility = Project['visibility']

const VISIBILITY_OPTIONS: {
  value: Visibility
  label: string
  desc: string
  icon: React.ElementType
  color: string
  bg: string
}[] = [
  {
    value: 'public',
    label: 'Public',
    desc: 'Visible to all members of the instance.',
    icon: Globe,
    color: 'oklch(0.55 0.18 150)',
    bg: 'oklch(0.96 0.04 150)',
  },
  {
    value: 'restricted',
    label: 'Restricted',
    desc: 'Only invited members can see this project.',
    icon: Users,
    color: 'oklch(0.58 0.14 55)',
    bg: 'oklch(0.97 0.03 55)',
  },
  {
    value: 'private',
    label: 'Private',
    desc: 'Only you can see this project.',
    icon: Lock,
    color: 'oklch(0.55 0.22 25)',
    bg: 'oklch(0.97 0.03 25)',
  },
]

function SettingSection({ title, desc, children }: {
  title: string
  desc?: string
  children: React.ReactNode
}) {
  return (
    <div className="grid grid-cols-1 gap-6 pb-7 border-b last:border-0 last:pb-0 md:grid-cols-[220px_1fr]">
      <div>
        <p className="text-sm font-semibold">{title}</p>
        {desc && <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{desc}</p>}
      </div>
      <div className="flex flex-col gap-4">{children}</div>
    </div>
  )
}

export function GeneralSettingsPage() {
  const { projectKey } = useParams<{ projectKey: string }>()
  const navigate = useNavigate()
  const { data: project } = useProjectByKey(projectKey)
  const updateProject = useUpdateProject(project?.id)
  const archiveProject = useArchiveProject(project?.id)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [visibility, setVisibility] = useState<Visibility>('restricted')
  const [confirmArchive, setConfirmArchive] = useState(false)
  const [saved, setSaved] = useState(false)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    if (!project) return
    setName(project.name)
    setDescription(project.description ?? '')
    setVisibility(project.visibility)
  }, [project])

  if (!project) return null

  const isDirty =
    name !== project.name ||
    description !== (project.description ?? '') ||
    visibility !== project.visibility

  async function handleSave() {
    if (!project) return
    await updateProject.mutateAsync({
      name: name.trim() || undefined,
      description: description.trim() || null,
      visibility,
      version: project.version,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  async function handleExport() {
    if (!project) return
    setExporting(true)
    try {
      await downloadProjectExport(project.id, project.key)
    } finally {
      setExporting(false)
    }
  }

  async function handleArchive() {
    await archiveProject.mutateAsync()
    navigate('/projects')
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-7">
      <div>
        <h1 className="text-xl font-semibold">General</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          <span className="font-mono font-semibold">{project.key}</span> · {project.name}
        </p>
      </div>

      <SettingSection title="Basic info" desc="Project name and description visible across the instance.">
        <div className="space-y-1.5">
          <Label htmlFor="proj-name" className="text-xs">Project name</Label>
          <input
            id="proj-name"
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary transition-colors"
          />
        </div>

        <div className="space-y-1.5">
          <div className="flex items-baseline gap-2">
            <Label className="text-xs">Key</Label>
            <span className="text-[11px] text-muted-foreground">— used as task prefix, cannot be changed</span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-32 rounded-md border border-input bg-muted px-3 py-2 text-sm font-mono font-semibold text-muted-foreground select-none">
              {project.key}
            </div>
            <div className="rounded-md border border-input bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              Preview: <strong className="text-foreground font-mono">{project.key}-42</strong>
            </div>
          </div>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="proj-desc" className="text-xs">Description</Label>
          <textarea
            id="proj-desc"
            rows={3}
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary transition-colors resize-y"
          />
        </div>
      </SettingSection>

      <SettingSection title="Visibility" desc="Controls who can see this project.">
        <div className="flex flex-col gap-2">
          {VISIBILITY_OPTIONS.map(opt => {
            const active = visibility === opt.value
            return (
              <div
                key={opt.value}
                onClick={() => setVisibility(opt.value)}
                className={cn(
                  'flex items-center gap-3 p-3.5 rounded-lg border-[1.5px] cursor-pointer transition-all',
                  active ? 'border-primary/60 bg-primary/5' : 'border-input hover:bg-muted/50',
                )}
              >
                <div
                  className="h-8 w-8 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: opt.bg }}
                >
                  <opt.icon className="h-4 w-4" style={{ color: opt.color }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold">{opt.label}</p>
                  <p className="text-xs text-muted-foreground">{opt.desc}</p>
                </div>
                <div
                  className="h-4 w-4 rounded-full border-2 shrink-0 transition-colors"
                  style={{
                    borderColor: active ? opt.color : 'var(--border)',
                    background: active ? opt.color : 'transparent',
                  }}
                />
              </div>
            )
          })}
        </div>
      </SettingSection>

      <div className="flex items-center gap-3">
        <Button
          onClick={handleSave}
          disabled={!isDirty || updateProject.isPending}
        >
          {updateProject.isPending ? 'Saving…' : saved ? 'Saved!' : 'Save changes'}
        </Button>
        {!isDirty && !saved && (
          <span className="text-xs text-muted-foreground">No unsaved changes</span>
        )}
      </div>

      <SettingSection
        title="Export"
        desc="Download all workflows, tasks, links and comments as a JSON file. Use for backups or to import into another environment via Projects → Import."
      >
        <div>
          <Button variant="outline" onClick={handleExport} disabled={exporting} className="gap-2">
            <Download className="h-4 w-4" />
            {exporting ? 'Exporting…' : 'Download JSON'}
          </Button>
        </div>
      </SettingSection>

      <div className="border-t pt-7 space-y-3">
        <p className="text-sm font-semibold text-destructive">Danger zone</p>
        <div className="rounded-lg border border-destructive/30 p-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium">Archive project</p>
            <p className="text-xs text-muted-foreground">
              Archived projects are hidden from the list but not deleted.
            </p>
          </div>
          {confirmArchive ? (
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-muted-foreground">Sure?</span>
              <Button
                size="sm" variant="destructive"
                onClick={handleArchive}
                disabled={archiveProject.isPending}
              >
                {archiveProject.isPending ? 'Archiving…' : 'Yes, archive'}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirmArchive(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <Button
              size="sm" variant="outline"
              className="shrink-0 border-destructive/40 text-destructive hover:bg-destructive/5"
              onClick={() => setConfirmArchive(true)}
            >
              Archive
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
