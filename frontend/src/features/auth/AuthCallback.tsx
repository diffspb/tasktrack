import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { userManager } from './oidc'

export function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    userManager.signinRedirectCallback()
      .then(() => navigate('/', { replace: true }))
      .catch(err => {
        console.error('OIDC callback error:', err)
        navigate('/', { replace: true })
      })
  }, [navigate])

  return (
    <div className="flex items-center justify-center h-screen text-sm text-muted-foreground">
      Signing in…
    </div>
  )
}
