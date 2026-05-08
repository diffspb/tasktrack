import { createContext, useContext, useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, STUB_USER_KEY } from '@/shared/api/client'

const IS_STUB = import.meta.env.VITE_AUTH_STUB === 'true'

interface User {
  id: string
  email: string
  display_name: string
  is_superuser: boolean
}

interface AuthCtx {
  user: User | null
  stubUsers: User[]
  switchStubUser: (email: string) => void
  isLoading: boolean
  logout: () => void
}

const AuthContext = createContext<AuthCtx>({
  user: null, stubUsers: [], switchStubUser: () => {}, isLoading: true, logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient()
  const [oidcReady, setOidcReady] = useState(IS_STUB)

  // Stub mode state
  const [stubEmail, setStubEmail] = useState<string | null>(() =>
    IS_STUB && typeof window !== 'undefined' ? window.localStorage.getItem(STUB_USER_KEY) : null
  )

  // OIDC: ensure user is logged in before attempting API calls
  useEffect(() => {
    if (IS_STUB) return
    let cancelled = false

    async function ensureAuth() {
      const { userManager } = await import('./oidc')
      const user = await userManager.getUser()
      if (cancelled) return
      if (!user || user.expired) {
        await userManager.signinRedirect()
      } else {
        setOidcReady(true)
      }
    }

    ensureAuth().catch(console.error)
    return () => { cancelled = true }
  }, [])

  // Current user — fetched once OIDC is ready (or immediately in stub mode)
  const { data: user, isLoading: meLoading } = useQuery<User>({
    queryKey: ['me', stubEmail],
    queryFn: () => api.get('/users/me').then(r => r.data),
    enabled: oidcReady,
  })

  // Stub users list — only in dev stub mode
  const { data: stubUsers = [] } = useQuery<User[]>({
    queryKey: ['dev', 'stub-users'],
    queryFn: () => api.get('/dev/stub-users').then(r => r.data).catch(() => []),
    enabled: IS_STUB,
    staleTime: Infinity,
  })

  // First boot: lock onto admin@localhost
  useEffect(() => {
    if (!IS_STUB || stubEmail || stubUsers.length === 0) return
    const admin = stubUsers.find(u => u.email === 'admin@localhost') ?? stubUsers[0]
    switchStubUser(admin.email)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stubUsers])

  function switchStubUser(email: string) {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STUB_USER_KEY, email)
    }
    setStubEmail(email)
    qc.invalidateQueries()
  }

  async function logout() {
    if (IS_STUB) return
    const { userManager } = await import('./oidc')
    await userManager.signoutRedirect()
  }

  return (
    <AuthContext value={{
      user: user ?? null,
      stubUsers: IS_STUB ? stubUsers : [],
      switchStubUser,
      isLoading: !oidcReady || meLoading,
      logout,
    }}>
      {children}
    </AuthContext>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
