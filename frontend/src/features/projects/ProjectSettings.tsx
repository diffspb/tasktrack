import { NavLink, Outlet, useParams } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useProject } from './api'

const TABS = [
  { to: 'team',     label: 'Team' },
  { to: 'workflow', label: 'Workflow' },
  { to: 'board',    label: 'Board' },
] as const

export function ProjectSettings() {
  const { id: projectId } = useParams<{ id: string }>()
  const { data: project } = useProject(projectId)

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        {project && (
          <p className="text-sm text-muted-foreground mt-1">
            <span className="font-mono font-semibold">{project.key}</span> · {project.name}
            {project.is_archived && (
              <Badge variant="outline" className="ml-2 text-[10px]">archived</Badge>
            )}
          </p>
        )}
      </div>

      {/* Tab navigation */}
      <nav className="flex border-b -mb-px">
        {TABS.map(tab => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              cn(
                'px-4 py-2 text-sm border-b-2 -mb-px transition-colors',
                isActive
                  ? 'border-primary text-foreground font-medium'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>

      {/* Sub-page content */}
      <Outlet />
    </div>
  )
}
