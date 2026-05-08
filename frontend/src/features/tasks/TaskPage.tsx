import { useState } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/features/auth/AuthProvider'
import { useProject } from '@/features/projects/api'
import { useTaskByKey } from './api'
import { TaskView } from './TaskView'

export function TaskPage() {
  const { key } = useParams<{ key: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const canGoBack = location.key !== 'default'
  const { user } = useAuth()
  const [copied, setCopied] = useState(false)

  const { data: task, isLoading, error } = useTaskByKey(key)
  const { data: project } = useProject(task?.project_id)

  function copyLink() {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto p-8 space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-muted-foreground">Task not found.</p>
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>Go back</Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="w-full px-6 xl:px-10 py-6 space-y-5">
        {/* Breadcrumb + actions row */}
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          {canGoBack && (
            <>
              <button
                onClick={() => navigate(-1)}
                className="flex items-center gap-1.5 hover:text-foreground transition-colors shrink-0"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <span className="text-muted-foreground/40">/</span>
            </>
          )}
          <span>{project?.name ?? '…'}</span>
          <span className="text-muted-foreground/40">/</span>
          <span className="font-semibold text-foreground">{task.key}</span>
          <button
            onClick={copyLink}
            className="ml-auto flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs hover:text-foreground transition-colors shrink-0"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? 'Copied' : 'Copy link'}
          </button>
        </div>

        <TaskView task={task} mode="page" currentUserId={user?.id ?? ''} />
      </div>
    </div>
  )
}
