import { Link, useMatch } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { useProject } from '@/features/projects/api'

export function Breadcrumbs() {
  const projectMatch = useMatch('/projects/:id/*')
  const projectId = projectMatch?.params.id
  const { data: project } = useProject(projectId)

  if (!projectId) {
    return <span className="text-sm font-medium text-muted-foreground">TaskTrack</span>
  }

  return (
    <nav className="flex items-center gap-1.5 text-sm">
      <Link to="/projects" className="text-muted-foreground hover:text-foreground transition-colors">
        Projects
      </Link>
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
      <span className="font-medium">
        {project ? project.name : <span className="text-muted-foreground">…</span>}
      </span>
      {project && (
        <span className="font-mono text-xs text-muted-foreground">{project.key}</span>
      )}
    </nav>
  )
}
