import { createContext, useContext, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, STUB_USER_KEY } from '@/shared/api/client'

interface User {
  id: string
  email: string
  display_name: string
}

interface AuthCtx {
  user: User | null
  stubUsers: User[]
  switchStubUser: (email: string) => void
  isLoading: boolean
}

const AuthContext = createContext<AuthCtx>({
  user: null, stubUsers: [], switchStubUser: () => {}, isLoading: true,
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient()
  const [stubEmail, setStubEmail] = useState<string | null>(() =>
    typeof window !== 'undefined' ? window.localStorage.getItem(STUB_USER_KEY) : null
  )

  // Current user — resolved by backend from X-Stub-User header (or default).
  const { data: user, isLoading: meLoading } = useQuery<User>({
    queryKey: ['me', stubEmail],
    queryFn: () => api.get('/users/me').then(r => r.data),
  })

  // Available stub users — only fetched in dev (AUTH_STUB=true). 404s in prod.
  const { data: stubUsers = [] } = useQuery<User[]>({
    queryKey: ['dev', 'stub-users'],
    queryFn: () => api.get('/dev/stub-users').then(r => r.data).catch(() => []),
    enabled: import.meta.env.DEV,
    staleTime: Infinity,
  })

  function switchStubUser(email: string) {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STUB_USER_KEY, email)
    }
    setStubEmail(email)
    // Force every query to refetch with the new identity.
    qc.invalidateQueries()
  }

  // First boot: lock onto admin@localhost so the chosen identity is explicit
  // and persisted, instead of relying on backend default.
  useEffect(() => {
    if (!stubEmail && stubUsers.length > 0) {
      const admin = stubUsers.find(u => u.email === 'admin@localhost') ?? stubUsers[0]
      switchStubUser(admin.email)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stubUsers])

  return (
    <AuthContext value={{
      user: user ?? null,
      stubUsers,
      switchStubUser,
      isLoading: meLoading,
    }}>
      {children}
    </AuthContext>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
