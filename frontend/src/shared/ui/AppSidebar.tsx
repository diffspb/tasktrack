import { useEffect } from 'react'
import { Zap, LayoutDashboard, Kanban, List, Settings } from 'lucide-react'
import { NavLink, useMatch } from 'react-router-dom'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupLabel,
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
} from '@/components/ui/sidebar'
import { useAuth } from '@/features/auth/AuthProvider'
import { useProject } from '@/features/projects/api'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

const LAST_PROJECT_KEY = 'tt_last_project'

const TOP_NAV = [
  { to: '/projects', icon: List, label: 'All Projects' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
]

const PROJECT_NAV = [
  { icon: Kanban,   label: 'Board',    suffix: 'board' },
  { icon: List,     label: 'Backlog',  suffix: 'backlog' },
  { icon: Settings, label: 'Settings', suffix: 'settings' },
]

export function AppSidebar() {
  const { user, stubUsers, switchStubUser } = useAuth()
  const projectMatch = useMatch('/projects/:id/*')
  const routeProjectId = projectMatch?.params.id

  // Remember last project; clear when user goes to /projects list
  const allProjectsMatch = useMatch('/projects')
  useEffect(() => {
    if (routeProjectId) {
      sessionStorage.setItem(LAST_PROJECT_KEY, routeProjectId)
    } else if (allProjectsMatch) {
      sessionStorage.removeItem(LAST_PROJECT_KEY)
    }
  }, [routeProjectId, allProjectsMatch])

  // Show project nav for current route OR last visited project
  const projectId = routeProjectId ?? sessionStorage.getItem(LAST_PROJECT_KEY) ?? undefined
  const { data: project } = useProject(projectId)

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex h-12 items-center gap-2.5 px-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
            <Zap className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="text-[15px] font-bold tracking-tight">TaskTrack</span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarMenu>
            {TOP_NAV.map(item => (
              <SidebarMenuItem key={item.to}>
                <NavLink to={item.to}>
                  {({ isActive }) => (
                    <SidebarMenuButton isActive={isActive}>
                      <item.icon />
                      <span>{item.label}</span>
                    </SidebarMenuButton>
                  )}
                </NavLink>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>

        {projectId && (
          <SidebarGroup>
            <SidebarGroupLabel className="flex items-center gap-1.5 truncate">
              <span className="truncate font-semibold text-foreground">
                {project?.name ?? '…'}
              </span>
              {project && (
                <span className="font-mono text-[10px] text-muted-foreground/70 shrink-0">
                  {project.key}
                </span>
              )}
            </SidebarGroupLabel>
            <SidebarMenu>
              {PROJECT_NAV.map(item => (
                <SidebarMenuItem key={item.suffix}>
                  <NavLink to={`/projects/${projectId}/${item.suffix}`}>
                    {({ isActive }) => (
                      <SidebarMenuButton isActive={isActive}>
                        <item.icon />
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    )}
                  </NavLink>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-xs">
                  {user?.display_name?.slice(0, 2).toUpperCase() ?? 'U'}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col text-left text-sm leading-tight">
                <span className="font-medium">{user?.display_name}</span>
                <span className="text-xs text-muted-foreground">{user?.email}</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
          {import.meta.env.DEV && stubUsers.length > 1 && (
            <SidebarMenuItem>
              <div className="px-2 pt-1">
                <label className="block text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/60 mb-1">
                  View as (dev)
                </label>
                <select
                  value={user?.email ?? ''}
                  onChange={e => switchStubUser(e.target.value)}
                  className="w-full rounded border border-border bg-background px-2 py-1 text-xs"
                >
                  {stubUsers.map(u => (
                    <option key={u.id} value={u.email}>
                      {u.display_name} — {u.email}
                    </option>
                  ))}
                </select>
              </div>
            </SidebarMenuItem>
          )}
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
