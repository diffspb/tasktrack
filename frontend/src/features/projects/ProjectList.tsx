import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useProjects, type Project } from './api'
import { CreateProjectModal } from './CreateProjectModal'
import { Plus, Users, Lock, Globe } from 'lucide-react'

const COLORS = [
  'oklch(0.52 0.16 252)', 'oklch(0.55 0.18 150)', 'oklch(0.58 0.18 30)',
  'oklch(0.52 0.18 290)', 'oklch(0.58 0.14 55)', 'oklch(0.50 0.16 200)',
]

function projectColor(key: string) {
  let h = 0
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) & 0xffff
  return COLORS[h % COLORS.length]
}

function VisibilityIcon({ v }: { v: Project['visibility'] }) {
  if (v === 'public') return <Globe className="h-3 w-3" />
  if (v === 'restricted') return <Users className="h-3 w-3" />
  return <Lock className="h-3 w-3" />
}

function ProjectCard({ project }: { project: Project }) {
  const color = projectColor(project.key)
  return (
    <div className="group flex flex-col overflow-hidden rounded-xl border bg-card shadow-sm transition-shadow hover:shadow-md">
      <div className="h-1 w-full" style={{ background: color }} />
      <div className="flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-[11px] font-bold text-white"
              style={{ background: color }}
            >
              {project.key.slice(0, 3)}
            </div>
            <div>
              <p className="font-semibold leading-tight">{project.name}</p>
              <p className="text-xs text-muted-foreground">{project.key}</p>
            </div>
          </div>
          <Badge variant="outline" className="shrink-0 gap-1 text-xs">
            <VisibilityIcon v={project.visibility} />
            {project.visibility}
          </Badge>
        </div>

        {project.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">{project.description}</p>
        )}

        <div className="mt-auto flex items-center justify-between text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            {project.members.length} member{project.members.length !== 1 ? 's' : ''}
          </span>
          <Button size="sm" variant="outline" className="h-7 text-xs">
            Open
          </Button>
        </div>
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="flex flex-col overflow-hidden rounded-xl border bg-card shadow-sm">
          <Skeleton className="h-1 w-full rounded-none" />
          <div className="flex flex-col gap-3 p-5">
            <div className="flex items-center gap-2.5">
              <Skeleton className="h-8 w-8 rounded-md" />
              <div className="space-y-1.5">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function ProjectList() {
  const { data: projects, isLoading, isError } = useProjects()
  const [createOpen, setCreateOpen] = useState(false)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground">All projects you have access to</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          New project
        </Button>
      </div>

      {isLoading && <LoadingSkeleton />}

      {isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          Failed to load projects. Make sure the backend is running.
        </div>
      )}

      {projects && projects.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <p className="text-muted-foreground">No projects yet.</p>
          <Button onClick={() => setCreateOpen(true)} variant="outline" className="gap-2">
            <Plus className="h-4 w-4" />
            Create your first project
          </Button>
        </div>
      )}

      {projects && projects.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map(p => <ProjectCard key={p.id} project={p} />)}
        </div>
      )}

      <CreateProjectModal open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
