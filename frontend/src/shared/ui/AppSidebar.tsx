import { useEffect } from 'react'
import { Zap, LayoutDashboard, Kanban, List, Network, Settings, ChevronRight, GanttChartSquare } from 'lucide-react'
import { NavLink, useMatch } from 'react-router-dom'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupLabel,
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
  SidebarMenuSub, SidebarMenuSubButton, SidebarMenuSubItem,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { useAuth } from '@/features/auth/AuthProvider'
import { useProjects, useProjectByKey } from '@/features/projects/api'
import { useProjectViews } from '@/features/projects/viewsApi'
import { useGanttCharts } from '@/features/timeline/ganttApi'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import type { View } from '@/features/projects/viewsApi'

const LAST_PROJECT_KEY = 'tt_last_project'
const MAX_SIDEBAR_PROJECTS = 5
const MAX_SIDEBAR_GANTTS = 5

const SETTINGS_NAV = [
  { label: 'General',       suffix: 'settings/general' },
  { label: 'Views',         suffix: 'settings/views' },
  { label: 'Team',          suffix: 'settings/team' },
  { label: 'Workflow',      suffix: 'settings/workflow' },
  { label: 'Board columns', suffix: 'settings/board' },
]

const VIEW_ICONS: Record<View['type'], React.ElementType> = {
  kanban:    Kanban,
  backlog:   List,
  epic_tree: Network,
}

const PROJECT_COLORS = [
  'oklch(0.52 0.16 252)', 'oklch(0.55 0.18 150)', 'oklch(0.58 0.18 30)',
  'oklch(0.52 0.18 290)', 'oklch(0.58 0.14 55)',  'oklch(0.50 0.16 200)',
]

function projectColor(key: string) {
  let h = 0
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) & 0xffff
  return PROJECT_COLORS[h % PROJECT_COLORS.length]
}

export function AppSidebar() {
  const { user, stubUsers, switchStubUser } = useAuth()
  const { data: projects } = useProjects()

  const projectMatch = useMatch('/projects/:projectKey/*')
  const viewMatch    = useMatch('/projects/:projectKey/views/:viewId')
  const taskMatch    = useMatch('/tasks/:taskKey')
  const routeProjectKey = projectMatch?.params.projectKey
  const routeViewId     = viewMatch?.params.viewId
  const allProjectsMatch = useMatch('/projects')
  const settingsMatch    = useMatch('/projects/:projectKey/settings/*')

  const taskProjectKey = taskMatch?.params.taskKey
    ? taskMatch.params.taskKey.substring(0, taskMatch.params.taskKey.lastIndexOf('-'))
    : undefined

  useEffect(() => {
    if (routeProjectKey) {
      sessionStorage.setItem(LAST_PROJECT_KEY, routeProjectKey)
    } else if (taskProjectKey) {
      sessionStorage.setItem(LAST_PROJECT_KEY, taskProjectKey)
    } else if (allProjectsMatch) {
      sessionStorage.removeItem(LAST_PROJECT_KEY)
    }
  }, [routeProjectKey, taskProjectKey, allProjectsMatch])

  const projectKey = routeProjectKey ?? taskProjectKey ?? sessionStorage.getItem(LAST_PROJECT_KEY) ?? undefined
  const { data: project } = useProjectByKey(projectKey)
  const { data: views }   = useProjectViews(project?.id)
  const { data: ganttCharts } = useGanttCharts()
  const ganttMatch = useMatch('/timeline/:ganttId/*')
  const currentGanttId = ganttMatch?.params.ganttId

  const sidebarProjects = (projects ?? []).slice(0, MAX_SIDEBAR_PROJECTS)
  const sidebarGantts   = (ganttCharts ?? []).slice(0, MAX_SIDEBAR_GANTTS)

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
        {/* Projects list */}
        <SidebarGroup>
          <SidebarGroupLabel>Projects</SidebarGroupLabel>
          <SidebarMenu>
            {sidebarProjects.map(p => (
              <SidebarMenuItem key={p.id}>
                <NavLink to={`/projects/${p.key}/board`}>
                  {() => (
                    <SidebarMenuButton isActive={projectKey === p.key}>
                      <div className="h-4 w-4 rounded shrink-0" style={{ background: projectColor(p.key) }} />
                      <span className="truncate">{p.name}</span>
                      <span className="ml-auto font-mono text-[10px] text-muted-foreground/50 shrink-0">
                        {p.key}
                      </span>
                    </SidebarMenuButton>
                  )}
                </NavLink>
              </SidebarMenuItem>
            ))}
            <SidebarMenuItem>
              <NavLink to="/projects" end>
                {({ isActive }) => (
                  <SidebarMenuButton isActive={isActive} className="text-muted-foreground">
                    <ChevronRight className="h-4 w-4" />
                    <span>All projects</span>
                  </SidebarMenuButton>
                )}
              </NavLink>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>

        <SidebarSeparator />

        {/* Personal section */}
        <SidebarGroup>
          <SidebarMenu>
            <SidebarMenuItem>
              <NavLink to="/dashboard">
                {({ isActive }) => (
                  <SidebarMenuButton isActive={isActive}>
                    <LayoutDashboard />
                    <span>My Dashboard</span>
                  </SidebarMenuButton>
                )}
              </NavLink>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>

        <SidebarSeparator />

        {/* Gantt charts */}
        <SidebarGroup>
          <SidebarGroupLabel>Timelines</SidebarGroupLabel>
          <SidebarMenu>
            {sidebarGantts.map(g => (
              <SidebarMenuItem key={g.id}>
                <NavLink to={`/timeline/${g.id}`}>
                  {() => (
                    <SidebarMenuButton isActive={currentGanttId === g.id}>
                      <GanttChartSquare className="h-4 w-4 shrink-0" />
                      <span className="truncate">{g.name}</span>
                    </SidebarMenuButton>
                  )}
                </NavLink>
              </SidebarMenuItem>
            ))}
            <SidebarMenuItem>
              <NavLink to="/timeline" end>
                {({ isActive }) => (
                  <SidebarMenuButton isActive={isActive} className="text-muted-foreground">
                    <ChevronRight className="h-4 w-4" />
                    <span>All timelines</span>
                  </SidebarMenuButton>
                )}
              </NavLink>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>

        {/* Current project nav */}
        {projectKey && (
          <>
            <SidebarSeparator />
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
                {/* Dynamic views list */}
                {(views ?? []).map(v => {
                  const Icon = VIEW_ICONS[v.type] ?? List
                  return (
                    <SidebarMenuItem key={v.id}>
                      <NavLink to={`/projects/${projectKey}/views/${v.id}`}>
                        {() => (
                          <SidebarMenuButton isActive={routeViewId === v.id}>
                            <Icon />
                            <span>{v.name}</span>
                          </SidebarMenuButton>
                        )}
                      </NavLink>
                    </SidebarMenuItem>
                  )
                })}

                {/* Settings with sub-items */}
                <SidebarMenuItem>
                  <NavLink to={`/projects/${projectKey}/settings`}>
                    {({ isActive }) => (
                      <SidebarMenuButton isActive={isActive}>
                        <Settings />
                        <span>Settings</span>
                      </SidebarMenuButton>
                    )}
                  </NavLink>
                  {settingsMatch && (
                    <SidebarMenuSub>
                      {SETTINGS_NAV.map(item => (
                        <SidebarMenuSubItem key={item.suffix}>
                          <NavLink to={`/projects/${projectKey}/${item.suffix}`}>
                            {({ isActive }) => (
                              <SidebarMenuSubButton isActive={isActive}>
                                {item.label}
                              </SidebarMenuSubButton>
                            )}
                          </NavLink>
                        </SidebarMenuSubItem>
                      ))}
                    </SidebarMenuSub>
                  )}
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroup>
          </>
        )}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          {user?.is_superuser && (
            <SidebarMenuItem>
              <NavLink to="/admin/settings">
                {({ isActive }) => (
                  <SidebarMenuButton isActive={isActive}>
                    <Settings />
                    <span>Global settings</span>
                  </SidebarMenuButton>
                )}
              </NavLink>
            </SidebarMenuItem>
          )}
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
