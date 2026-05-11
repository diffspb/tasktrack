import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'
import { useAuth } from '@/features/auth/AuthProvider'
import { Shield } from 'lucide-react'

interface UserRow {
  id: string
  email: string
  display_name: string
  is_superuser: boolean
}

function initials(name: string) {
  return name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() || '?'
}

export function UsersSettingsPage() {
  const { user: me } = useAuth()
  const [search, setSearch] = useState('')

  const { data: users = [], isLoading } = useQuery<UserRow[]>({
    queryKey: ['admin-users'],
    queryFn: () => api.get('/users/search').then(r => r.data),
    staleTime: 60_000,
  })

  const filtered = search.trim()
    ? users.filter(u =>
        u.display_name.toLowerCase().includes(search.toLowerCase()) ||
        u.email.toLowerCase().includes(search.toLowerCase()),
      )
    : users

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Users</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          All registered users · {users.length} total
        </p>
      </div>

      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="Filter by name or email…"
        className="w-full max-w-sm rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:border-primary transition-colors"
      />

      {isLoading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/40 text-xs text-muted-foreground">
                <th className="px-4 py-2.5 text-left font-medium">User</th>
                <th className="px-4 py-2.5 text-left font-medium">Email</th>
                <th className="px-4 py-2.5 text-left font-medium">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {filtered.map(u => (
                <tr key={u.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2.5">
                      <div className="h-7 w-7 rounded-full bg-muted-foreground/15 flex items-center justify-center text-[11px] font-bold shrink-0">
                        {initials(u.display_name)}
                      </div>
                      <span className="font-medium">
                        {u.display_name}
                        {u.id === me?.id && (
                          <span className="ml-1.5 text-xs text-muted-foreground">(you)</span>
                        )}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-muted-foreground">{u.email}</td>
                  <td className="px-4 py-2.5">
                    {u.is_superuser ? (
                      <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-[11px] font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300">
                        <Shield className="h-3 w-3" /> Superuser
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">User</span>
                    )}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-sm text-muted-foreground">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
