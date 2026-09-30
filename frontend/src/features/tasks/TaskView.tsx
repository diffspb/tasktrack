import { useDisplayWorkflows, useProjectMembers, type Status, type Task } from './api'
import { ResultSection } from '@/features/results/ResultSection'
import { SessionPanel } from '@/features/results/SessionPanel'
import { WorkPackagePanel } from '@/features/results/WorkPackagePanel'
import { ActivityBlock } from './task-view/ActivityBlock'
import { ChildTasks } from './task-view/ChildTasks'
import { DatesBlock } from './task-view/DatesBlock'
import { DescriptionEditor } from './task-view/DescriptionEditor'
import { DetailsBlock } from './task-view/DetailsBlock'
import { PeopleBlock } from './task-view/PeopleBlock'
import { RelationsBlock } from './task-view/RelationsBlock'
import { StatusActions } from './task-view/StatusActions'
import { TitleEditor } from './task-view/TitleEditor'

interface Props {
  task: Task
  mode: 'page' | 'panel'
  currentUserId: string
}

function DebugBlock({ task }: { task: Task }) {
  return (
    <details className="border-t pt-4">
      <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/40 hover:text-muted-foreground select-none">
        Debug
      </summary>
      <div className="mt-3">
        <pre className="rounded-md bg-muted p-3 text-[11px] font-mono overflow-x-auto whitespace-pre-wrap break-all leading-relaxed">
          {JSON.stringify(task, null, 2)}
        </pre>
      </div>
    </details>
  )
}

/** Task card: composes the blocks in `task-view/` and `features/results/` for page or side panel. */
export function TaskView({ task, mode, currentUserId }: Props) {
  const { data: workflows = [] } = useDisplayWorkflows(task.project_id)
  const { data: members } = useProjectMembers(task.project_id)

  // The task's own workflow — for process types a system one (ADR-023), never the project default.
  const taskWorkflow = workflows.find(w => w.id === task.workflow_id)
  const statuses: Status[] = [...(taskWorkflow?.statuses ?? [])].sort((a, b) => a.position - b.position)
  const transitions = taskWorkflow?.transitions ?? []
  const currentStatus = statuses.find(s => s.id === task.current_status_id)
  const allStatuses = workflows.flatMap(w => w.statuses)

  const memberList = members?.items ?? []
  const userById = new Map(memberList.map(m => [m.user.id, m.user]))
  const nameOf = (id: string) => userById.get(id)?.display_name ?? id.slice(0, 8)
  const me = memberList.find(m => m.user.id === currentUserId)
  const isManager = me?.role === 'admin' || me?.role === 'manager'

  const title = <TitleEditor task={task} mode={mode} />
  const actions = <StatusActions task={task} statuses={statuses} transitions={transitions} mode={mode} />
  const details = <DetailsBlock task={task} currentStatus={currentStatus} />
  const description = <DescriptionEditor task={task} />
  const workPackage = <WorkPackagePanel task={task} canEdit={task.reporter_id === currentUserId || isManager} />
  const result = <ResultSection task={task} currentUserId={currentUserId} members={memberList} />
  const session = <SessionPanel task={task} currentUserId={currentUserId} isManager={isManager} nameOf={nameOf} />
  const children = <ChildTasks task={task} statuses={allStatuses} />
  const relations = <RelationsBlock task={task} />
  const people = <PeopleBlock task={task} currentUserId={currentUserId} members={memberList} isManager={isManager} />
  const dates = <DatesBlock task={task} />
  const activity = <ActivityBlock taskId={task.id} currentUserId={currentUserId} userById={userById} nameOf={nameOf} />
  const debug = <DebugBlock task={task} />

  if (mode === 'page') {
    return (
      <div className="space-y-5">
        {title}
        {actions}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] xl:grid-cols-[1fr_300px] gap-6 pt-1">
          <div className="min-w-0 space-y-6">
            {details}
            {description}
            {workPackage}
            {result}
            {children}
            {relations}
            {activity}
            {debug}
          </div>
          <div className="space-y-4">
            {people}
            {session}
            {dates}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-5">
      {title}
      {actions}
      {details}
      {description}
      {workPackage}
      {result}
      {session}
      {children}
      {relations}
      {people}
      {dates}
      {activity}
      {debug}
    </div>
  )
}
