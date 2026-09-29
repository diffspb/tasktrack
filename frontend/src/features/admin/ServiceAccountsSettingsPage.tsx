import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Copy, KeyRound, Plus, RotateCw, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/shared/api/client'
import { useAuth } from '@/features/auth/AuthProvider'

interface ServiceAccount { id: string; email: string; display_name: string; is_active: boolean; created_at: string }
interface ApiKey {
  id: string; user_id: string; name: string; prefix: string; created_at: string
  expires_at: string | null; revoked_at: string | null; last_used_at: string | null
}
type IssuedKey = ApiKey & { token: string }

const fmt = (s: string | null) => (s ? new Date(s).toLocaleString('en', { dateStyle: 'medium', timeStyle: 'short' }) : '—')
const inputCls = 'rounded-md border border-input bg-background px-2.5 py-1.5 text-sm outline-none focus:border-primary'

/**
 * Service accounts for agents and integrations and their API keys (ADR-017).
 * Superuser only. A key's token is shown once, right after issue or rotation.
 */
export function ServiceAccountsSettingsPage() {
  const { user } = useAuth()
  const qc = useQueryClient()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [issued, setIssued] = useState<IssuedKey | null>(null)

  const { data: accounts = [], isLoading } = useQuery<ServiceAccount[]>({
    queryKey: ['service-accounts'],
    queryFn: () => api.get('/admin/service-accounts').then(r => r.data),
    enabled: !!user?.is_superuser,
  })
  const create = useMutation({
    mutationFn: () => api.post('/admin/service-accounts', { email, display_name: name }).then(r => r.data),
    onSuccess: () => { setEmail(''); setName(''); qc.invalidateQueries({ queryKey: ['service-accounts'] }) },
  })
  const setActive = useMutation({
    mutationFn: (a: ServiceAccount) =>
      api.patch(`/admin/service-accounts/${a.id}`, { is_active: !a.is_active }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['service-accounts'] }),
  })

  if (!user?.is_superuser) {
    return <p className="text-sm text-muted-foreground">Only a superuser manages service accounts.</p>
  }

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Service accounts</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Accounts for agents and integrations. Their rights come from project membership; a viewer is read-only.
          The same key works for REST and MCP (<code>Authorization: Bearer tt_…</code>).
        </p>
      </div>

      {issued && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 dark:bg-amber-900/20 p-3 space-y-2" data-testid="issued-token">
          <p className="text-sm font-medium">Copy the token now — it will not be shown again.</p>
          <div className="flex gap-2 items-center">
            <code className="flex-1 break-all rounded bg-background px-2 py-1 text-xs">{issued.token}</code>
            <Button size="sm" variant="outline" onClick={() => navigator.clipboard?.writeText(issued.token)}>
              <Copy className="h-3.5 w-3.5 mr-1" />Copy
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setIssued(null)}>Done</Button>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <input aria-label="Service account email" className={`${inputCls} flex-1`} placeholder="agent@agents" value={email}
          onChange={e => setEmail(e.target.value)} />
        <input aria-label="Service account name" className={`${inputCls} flex-1`} placeholder="Display name" value={name}
          onChange={e => setName(e.target.value)} />
        <Button size="sm" disabled={!email.trim() || !name.trim() || create.isPending} onClick={() => create.mutate()}>
          <Plus className="h-3.5 w-3.5 mr-1" />Create
        </Button>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : (
        <ul className="space-y-3">
          {accounts.map(a => (
            <li key={a.id} className="rounded-lg border p-3 space-y-2">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium flex-1">
                  {a.display_name} <span className="text-muted-foreground font-normal">{a.email}</span>
                </p>
                <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setActive.mutate(a)}>
                  {a.is_active ? 'Deactivate' : 'Activate'}
                </Button>
              </div>
              <AccountKeys account={a} onIssued={setIssued} />
            </li>
          ))}
          {accounts.length === 0 && <li className="text-sm text-muted-foreground">No service accounts yet.</li>}
        </ul>
      )}
    </div>
  )
}

function AccountKeys({ account, onIssued }: { account: ServiceAccount; onIssued: (k: IssuedKey) => void }) {
  const qc = useQueryClient()
  const [keyName, setKeyName] = useState('')
  const [days, setDays] = useState('')
  const queryKey = ['api-keys', account.id]
  const { data: keys = [] } = useQuery<ApiKey[]>({
    queryKey,
    queryFn: () => api.get(`/admin/service-accounts/${account.id}/api-keys`).then(r => r.data),
  })
  const refresh = () => qc.invalidateQueries({ queryKey })
  const issue = useMutation({
    mutationFn: () => api.post(`/admin/service-accounts/${account.id}/api-keys`, {
      name: keyName,
      expires_at: days ? new Date(Date.now() + Number(days) * 86_400_000).toISOString() : null,
    }).then(r => r.data as IssuedKey),
    onSuccess: k => { onIssued(k); setKeyName(''); setDays(''); refresh() },
  })
  const revoke = useMutation({ mutationFn: (id: string) => api.delete(`/admin/api-keys/${id}`), onSuccess: refresh })
  const rotate = useMutation({
    mutationFn: (id: string) => api.post(`/admin/api-keys/${id}/rotate`).then(r => r.data as IssuedKey),
    onSuccess: k => { onIssued(k); refresh() },
  })

  return (
    <div className="space-y-2">
      {keys.length > 0 && (
        <table className="w-full text-xs">
          <thead className="text-muted-foreground">
            <tr><th className="text-left font-medium">Key</th><th className="text-left font-medium">Name</th>
              <th className="text-left font-medium">Expires</th><th className="text-left font-medium">Last used</th><th /></tr>
          </thead>
          <tbody>
            {keys.map(k => (
              <tr key={k.id} className={k.revoked_at ? 'text-muted-foreground line-through' : ''}>
                <td className="font-mono py-1">{k.prefix}…</td>
                <td>{k.name}</td>
                <td>{fmt(k.expires_at)}</td>
                <td>{fmt(k.last_used_at)}</td>
                <td className="text-right">
                  {!k.revoked_at && (
                    <>
                      <button title="Rotate" className="p-1 hover:text-foreground" onClick={() => rotate.mutate(k.id)}>
                        <RotateCw className="h-3.5 w-3.5" />
                      </button>
                      <button title="Revoke" className="p-1 hover:text-destructive" onClick={() => revoke.mutate(k.id)}>
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="flex gap-2">
        <input aria-label={`Key name for ${account.email}`} className={`${inputCls} flex-1`} placeholder="Key name (e.g. laptop)"
          value={keyName} onChange={e => setKeyName(e.target.value)} />
        <input aria-label="Expires in days" className={`${inputCls} w-32`} placeholder="expires, days" value={days}
          onChange={e => setDays(e.target.value.replace(/\D/g, ''))} />
        <Button size="sm" variant="outline" disabled={!keyName.trim() || issue.isPending || !account.is_active}
          onClick={() => issue.mutate()}>
          <KeyRound className="h-3.5 w-3.5 mr-1" />Issue key
        </Button>
      </div>
    </div>
  )
}
