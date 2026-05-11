import { NavLink, Outlet } from 'react-router-dom'
import { Link2, Users } from 'lucide-react'
import { cn } from '@/lib/utils'

const NAV = [
  { label: 'Users',      path: 'users',      icon: Users },
  { label: 'Link types', path: 'link-types', icon: Link2 },
]

export function GlobalSettingsLayout() {
  return (
    <div className="flex h-full">
      {/* Sidebar nav */}
      <aside className="w-48 shrink-0 border-r p-4 space-y-1">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Global settings
        </p>
        {NAV.map(({ label, path, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) => cn(
              'flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors',
              isActive
                ? 'bg-primary/10 text-primary font-medium'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted',
            )}
          >
            <Icon className="h-3.5 w-3.5 shrink-0" />
            {label}
          </NavLink>
        ))}
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  )
}
