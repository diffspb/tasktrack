import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Trash2, UserPlus } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { api } from '@/shared/api/client'
import { useProject } from './api'
import { useAuth } from '@/features/auth/AuthProvider'
import type { ProjectMember } from '@/features/tasks/api'
import { WorkflowEditor } from './WorkflowEditor'

const ROLES = ['admin', 'manager', 'member', 'viewer'] as const
type Role = typeof ROLES[number]

function useProjectMembers(projectId: string | undefined) {
  return useQuery<{ items: ProjectMember[] }>({
    queryKey: ['project-members', projectId],
    queryFn: () => api.get(`/projects/${projectId}/members`).then(r => r.data),
    enabled: !!projectId,
  })
}

function useAddMember(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ user_id, role }: { user_id: string; role: string }) =>
      api.post(`/projects/${projectId}/members`, { user_id, role }).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-members', projectId] }),
  })
}

function useRemoveMember(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      api.delete(`/projects/${projectId}/members/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-members', projectId] }),
  })
}

const ROLE_STYLES: Record<Role, string> = {
  admin:   'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  manager: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  member:  'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  viewer:  'bg-muted text-muted-foreground',
}

export function ProjectSettings() {
  const { id: projectId } = useParams<{ id: string }>()
  const { user } = useAuth()
  const { data: project } = useProject(projectId)
  const { data: membersData, isLoading } = useProjectMembers(projectId)
  const addMember = useAddMember(projectId ?? '')
  const removeMember = useRemoveMember(projectId ?? '')

  const [newUserId, setNewUserId] = useState('')
  const [newRole, setNewRole] = useState<Role>('member')
  const [addError, setAddError] = useState<string | null>(null)

  const members = membersData?.items ?? []
  const myRole = members.find(m => m.user.id === user?.id)?.role
  const canManage = myRole === 'admin' || myRole === 'manager'

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    if (!newUserId.trim()) return
    setAddError(null)
    try {
      await addMember.mutateAsync({ user_id: newUserId.trim(), role: newRole })
      setNewUserId('')
    } catch {
      setAddError('Could not add member. Check the user ID.')
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-8">
      {/* Project info */}
      <div>
        <h1 className="text-xl font-semibold">Settings</h1>
        {project && (
          <p className="text-sm text-muted-foreground mt-1">
            <span className="font-mono font-semibold">{project.key}</span> · {project.name}
            {project.is_archived && (
              <Badge variant="outline" className="ml-2 text-[10px]">archived</Badge>
            )}
          </p>
        )}
      </div>

      {/* Members */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold">Members</h2>
          <p className="text-sm text-muted-foreground">Manage who has access to this project.</p>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : (
          <ul className="divide-y rounded-lg border overflow-hidden">
            {members.map(m => {
              const roleCls = ROLE_STYLES[m.role as Role] ?? ROLE_STYLES.viewer
              const isMe = m.user.id === user?.id
              return (
                <li key={m.user.id} className="flex items-center gap-3 px-4 py-2.5 bg-background">
                  <div className="h-8 w-8 rounded-full bg-muted-foreground/15 flex items-center justify-center text-xs font-bold shrink-0">
                    {m.user.display_name.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">
                      {m.user.display_name}
                      {isMe && <span className="ml-1.5 text-muted-foreground text-xs">(you)</span>}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">{m.user.email}</p>
                  </div>
                  <span className={`rounded px-2 py-0.5 text-[11px] font-medium capitalize ${roleCls}`}>
                    {m.role}
                  </span>
                  {canManage && !isMe && (
                    <button
                      onClick={() => removeMember.mutate(m.user.id)}
                      disabled={removeMember.isPending}
                      className="rounded p-1.5 text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors"
                      title="Remove member"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}

        {canManage && (
          <form onSubmit={handleAdd} className="space-y-3 rounded-lg border p-4">
            <p className="text-sm font-medium flex items-center gap-1.5">
              <UserPlus className="h-4 w-4" /> Add member
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="member-id" className="text-xs">User ID</Label>
                <Input
                  id="member-id"
                  value={newUserId}
                  onChange={e => setNewUserId(e.target.value)}
                  placeholder="UUID"
                  className="h-8 text-xs font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="member-role" className="text-xs">Role</Label>
                <select
                  id="member-role"
                  value={newRole}
                  onChange={e => setNewRole(e.target.value as Role)}
                  className="w-full h-8 rounded-md border border-input bg-background px-3 text-xs"
                >
                  {ROLES.map(r => <option key={r} value={r} className="capitalize">{r}</option>)}
                </select>
              </div>
            </div>
            {addError && <p className="text-xs text-destructive">{addError}</p>}
            <Button type="submit" size="sm" disabled={!newUserId.trim() || addMember.isPending} className="h-7 text-xs">
              {addMember.isPending ? 'Adding…' : 'Add'}
            </Button>
          </form>
        )}
      </section>

      {/* Workflow */}
      <section className="space-y-4">
        <div>
          <h2 className="text-base font-semibold">Workflow</h2>
          <p className="text-sm text-muted-foreground">Statuses and allowed transitions for this project.</p>
        </div>
        {projectId && <WorkflowEditor projectId={projectId} />}
      </section>
    </div>
  )
}
