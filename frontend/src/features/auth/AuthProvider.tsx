import { createContext, useContext } from 'react'

interface User {
  id: string
  email: string
  display_name: string
}

interface AuthCtx {
  user: User | null
}

const AuthContext = createContext<AuthCtx>({ user: null })

// Stub mode: no Keycloak, fixed user from AUTH_STUB backend.
// Phase 6 will replace this with OIDC flow.
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const user: User = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'dev@localhost',
    display_name: 'Dev User',
  }
  return <AuthContext value={{ user }}>{children}</AuthContext>
}

export function useAuth() {
  return useContext(AuthContext)
}
