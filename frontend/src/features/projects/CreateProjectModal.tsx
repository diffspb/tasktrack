import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useCreateProject } from './api'

interface Props {
  open: boolean
  onClose: () => void
}

export function CreateProjectModal({ open, onClose }: Props) {
  const [name, setName] = useState('')
  const [key, setKey] = useState('')
  const [visibility, setVisibility] = useState<'public' | 'restricted' | 'private'>('restricted')
  const [error, setError] = useState<string | null>(null)
  const create = useCreateProject()

  function handleNameChange(v: string) {
    setName(v)
    if (!key || key === autoKey(name)) setKey(autoKey(v))
  }

  function autoKey(n: string) {
    return n.trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !key.trim()) return
    setError(null)
    try {
      await create.mutateAsync({ name: name.trim(), key: key.trim(), visibility })
      setName('')
      setKey('')
      setVisibility('restricted')
      onClose()
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      if (code === 'DUPLICATE_PROJECT_KEY') {
        setError(`Key "${key.trim()}" is already taken. Choose another.`)
      } else {
        setError('Something went wrong. Please try again.')
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) { setError(null); onClose() } }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>New project</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="proj-name">Name</Label>
            <Input
              id="proj-name"
              value={name}
              onChange={e => handleNameChange(e.target.value)}
              placeholder="My project"
              autoFocus
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="proj-key">Key</Label>
            <Input
              id="proj-key"
              value={key}
              onChange={e => setKey(e.target.value.toUpperCase())}
              placeholder="PROJ"
              maxLength={10}
            />
            <p className="text-xs text-muted-foreground">Tasks will be prefixed: {key || 'KEY'}-1</p>
          </div>
          <div className="space-y-1.5">
            <Label>Visibility</Label>
            <div className="flex gap-2">
              {(['public', 'restricted', 'private'] as const).map(v => (
                <button
                  key={v}
                  type="button"
                  onClick={() => setVisibility(v)}
                  className={`flex-1 rounded-md border px-3 py-2 text-sm capitalize transition-colors ${
                    visibility === v
                      ? 'border-primary bg-primary/10 text-primary font-medium'
                      : 'border-border hover:border-border/80 text-muted-foreground'
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>
          {error && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={!name.trim() || !key.trim() || create.isPending}>
              {create.isPending ? 'Creating…' : 'Create project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
