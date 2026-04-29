import { Zap, LayoutDashboard, Kanban, List, Users, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import {
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupLabel,
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem,
} from '@/components/ui/sidebar'
import { useAuth } from '@/features/auth/AuthProvider'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'

const NAV_ITEMS = [
  { to: '/projects', icon: List, label: 'All Projects' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
]

const PROJECT_NAV = [
  { icon: Kanban, label: 'Board', suffix: 'board' },
  { icon: List, label: 'Backlog', suffix: 'backlog' },
  { icon: Users, label: 'Members', suffix: 'members' },
  { icon: Settings, label: 'Settings', suffix: 'settings' },
]

export function AppSidebar() {
  const { user } = useAuth()

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
            {NAV_ITEMS.map(item => (
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

        <SidebarGroup>
          <SidebarGroupLabel>Project</SidebarGroupLabel>
          <SidebarMenu>
            {PROJECT_NAV.map(item => (
              <SidebarMenuItem key={item.suffix}>
                <SidebarMenuButton disabled className="text-muted-foreground/50">
                  <item.icon />
                  <span>{item.label}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
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
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
