import { useParams } from 'react-router-dom'
import { RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  useProjectWorkflows, useTaskTypeConfigs, useSetTaskTypeWorkflow, useResetTaskTypeWorkflow,
} from './workflowApi'
import { WorkflowEditor } from './WorkflowEditor'

const TYPE_ICONS: Record<string, string> = {
  task:     '☑',
  bug:      '🐛',
  story:    '📖',
  epic:     '⚡',
  decision: '🔀',
}

function TaskTypeWorkflowTable({ projectId }: { projectId: string }) {
  const { data: configs, isLoading: cfgLoading } = useTaskTypeConfigs(projectId)
  const { data: workflows = [], isLoading: wfLoading } = useProjectWorkflows(projectId)
  const setWf = useSetTaskTypeWorkflow(projectId)
  const resetWf = useResetTaskTypeWorkflow(projectId)

  if (cfgLoading || wfLoading) {
    return <div className="space-y-2">{[1, 2, 3].map(i => <Skeleton key={i} className="h-10 w-full" />)}</div>
  }

  const items = configs?.items ?? []

  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">Type</th>
            <th className="text-left px-4 py-2 text-xs font-semibold text-muted-foreground">Workflow</th>
            <th className="w-8" />
          </tr>
        </thead>
        <tbody className="divide-y">
          {items.map(cfg => (
            <tr key={cfg.task_type_id} className="bg-background">
              <td className="px-4 py-2.5">
                <span className="flex items-center gap-2">
                  <span>{TYPE_ICONS[cfg.task_type_key] ?? '•'}</span>
                  <span className="font-medium">{cfg.task_type_name}</span>
                  {!cfg.is_project_override && (
                    <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">system default</span>
                  )}
                </span>
              </td>
              <td className="px-4 py-2.5">
                <select
                  value={cfg.workflow_id ?? ''}
                  onChange={async e => {
                    const val = e.target.value
                    if (val === '') {
                      await resetWf.mutateAsync(cfg.task_type_id)
                    } else {
                      await setWf.mutateAsync({ taskTypeId: cfg.task_type_id, workflowId: val })
                    }
                  }}
                  className="h-7 rounded-md border border-input bg-background px-2 text-xs min-w-[160px]"
                >
                  <option value="">System default</option>
                  {workflows.map(wf => (
                    <option key={wf.id} value={wf.id}>
                      {wf.name}{wf.is_default ? ' (default)' : ''}
                    </option>
                  ))}
                </select>
              </td>
              <td className="px-2 py-2.5">
                {cfg.is_project_override && (
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
                    title="Reset to system default"
                    onClick={() => resetWf.mutate(cfg.task_type_id)}
                    disabled={resetWf.isPending}
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function WorkflowSettingsPage() {
  const { id: projectId } = useParams<{ id: string }>()
  if (!projectId) return null

  return (
    <div className="space-y-8">
      {/* Task type workflow mapping */}
      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold">Workflow per task type</h2>
          <p className="text-sm text-muted-foreground">
            Choose which workflow each task type uses. Defaults to the system workflow if not set.
          </p>
        </div>
        <TaskTypeWorkflowTable projectId={projectId} />
      </section>

      {/* Workflow editor */}
      <section className="space-y-3">
        <div>
          <h2 className="text-base font-semibold">Workflow editor</h2>
          <p className="text-sm text-muted-foreground">
            Configure statuses and allowed transitions for each workflow.
          </p>
        </div>
        <WorkflowEditor projectId={projectId} />
      </section>
    </div>
  )
}
