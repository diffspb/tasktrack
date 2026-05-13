import { CheckCircle2, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/features/auth/AuthProvider'
import { useSystemStatus, useInitializeSystem } from './api'

export function SystemSettingsPage() {
  const { user } = useAuth()
  const { data: status, isLoading } = useSystemStatus()
  const init = useInitializeSystem()

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>

  const initialized = status?.initialized ?? false

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h2 className="text-lg font-semibold">System initialization</h2>
        <p className="text-sm text-muted-foreground mt-1">
          System data includes task types, link types, and built-in workflows.
        </p>
      </div>

      <div className={`flex items-start gap-3 rounded-lg border p-4 ${
        initialized ? 'border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30' : 'border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30'
      }`}>
        {initialized ? (
          <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        )}
        <div className="space-y-1">
          <p className="text-sm font-medium">
            {initialized ? 'System is initialized' : 'System is not initialized'}
          </p>
          <p className="text-sm text-muted-foreground">
            {initialized
              ? 'Task types, link types and system workflows are present in the database.'
              : 'Task types, link types and system workflows are missing. Tasks cannot be created until the system is initialized.'}
          </p>
        </div>
      </div>

      {!initialized && user?.is_superuser && (
        <Button
          onClick={() => init.mutate()}
          disabled={init.isPending}
        >
          {init.isPending ? 'Initializing…' : 'Initialize system'}
        </Button>
      )}

      {!initialized && !user?.is_superuser && (
        <p className="text-sm text-muted-foreground">
          Contact an administrator to initialize the system.
        </p>
      )}
    </div>
  )
}
