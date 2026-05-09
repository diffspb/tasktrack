import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AxiosError } from 'axios'
import { Upload } from 'lucide-react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useImportProject } from './api'

interface Props {
  open: boolean
  onClose: () => void
}

function Toggle({ checked, onChange, label, desc }: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  desc: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex items-start gap-3 w-full text-left"
    >
      <div className={`mt-0.5 h-5 w-9 shrink-0 rounded-full border-2 transition-colors relative ${
        checked ? 'bg-primary border-primary' : 'bg-muted border-border'
      }`}>
        <span className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0.5'
        }`} />
      </div>
      <div>
        <p className="text-sm font-medium leading-tight">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
      </div>
    </button>
  )
}

export function ImportProjectDialog({ open, onClose }: Props) {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [fileData, setFileData] = useState<Record<string, unknown> | null>(null)
  const [fileName, setFileName] = useState('')
  const [newKey, setNewKey] = useState('')
  const [includeComments, setIncludeComments] = useState(true)
  const [resetStatuses, setResetStatuses] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const importProject = useImportProject()

  function handleClose() {
    setFileData(null)
    setFileName('')
    setNewKey('')
    setIncludeComments(true)
    setResetStatuses(false)
    setFileError(null)
    setSubmitError(null)
    onClose()
  }

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setFileError(null)
    const reader = new FileReader()
    reader.onload = ev => {
      try {
        const parsed = JSON.parse(ev.target?.result as string)
        if (!parsed?.project || !parsed?.tasks) {
          setFileError('Invalid export file — missing required fields.')
          return
        }
        setFileData(parsed)
        setFileName(file.name)
        if (!newKey && parsed.project?.key) {
          setNewKey((parsed.project.key as string).slice(0, 6) + 'I')
        }
      } catch {
        setFileError('Could not parse JSON file.')
      }
    }
    reader.readAsText(file)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!fileData || !newKey.trim()) return
    setSubmitError(null)
    try {
      const project = await importProject.mutateAsync({
        data: fileData,
        new_key: newKey.trim(),
        include_comments: includeComments,
        reset_statuses: resetStatuses,
      })
      handleClose()
      navigate(`/projects/${project.key}/board`)
    } catch (err) {
      const code = (err as AxiosError<{ detail: { code: string } }>)?.response?.data?.detail?.code
      if (code === 'DUPLICATE_PROJECT_KEY') {
        setSubmitError(`Key "${newKey.trim()}" is already taken. Choose another.`)
      } else {
        setSubmitError('Import failed. Check that the file is a valid export.')
      }
    }
  }

  const taskCount = Array.isArray((fileData as Record<string, unknown> | null)?.tasks)
    ? ((fileData as Record<string, unknown>).tasks as unknown[]).length
    : null

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) handleClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Import project</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* File picker */}
          <div className="space-y-2">
            <Label>Export file</Label>
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className={`flex w-full flex-col items-center gap-2 rounded-lg border-2 border-dashed px-4 py-5 text-center transition-colors hover:bg-muted/50 ${
                fileData ? 'border-primary/40 bg-primary/5' : 'border-border'
              }`}
            >
              <Upload className="h-5 w-5 text-muted-foreground" />
              {fileData ? (
                <>
                  <span className="text-sm font-medium">{fileName}</span>
                  <span className="text-xs text-muted-foreground">
                    {taskCount} task{taskCount !== 1 ? 's' : ''} · click to change
                  </span>
                </>
              ) : (
                <>
                  <span className="text-sm font-medium">Choose JSON file</span>
                  <span className="text-xs text-muted-foreground">Export from Settings → General → Export</span>
                </>
              )}
            </button>
            <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={handleFile} />
            {fileError && (
              <p className="text-xs text-destructive">{fileError}</p>
            )}
          </div>

          {/* New key */}
          <div className="space-y-1.5">
            <Label htmlFor="import-key">New project key</Label>
            <Input
              id="import-key"
              value={newKey}
              onChange={e => setNewKey(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 10))}
              placeholder="PROJ"
              maxLength={10}
            />
            <p className="text-xs text-muted-foreground">Tasks will be renumbered: {newKey || 'KEY'}-1, {newKey || 'KEY'}-2…</p>
          </div>

          {/* Options */}
          <div className="space-y-3 rounded-lg border bg-muted/30 p-3">
            <Toggle
              checked={includeComments}
              onChange={setIncludeComments}
              label="Include comments"
              desc="Restore all task comments and replies"
            />
            <Toggle
              checked={resetStatuses}
              onChange={setResetStatuses}
              label="Reset task statuses"
              desc="Move all tasks to the initial status instead of restoring the original"
            />
          </div>

          {submitError && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{submitError}</p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>Cancel</Button>
            <Button
              type="submit"
              disabled={!fileData || !newKey.trim() || importProject.isPending}
            >
              {importProject.isPending ? 'Importing…' : 'Import project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
