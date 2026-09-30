import { useState } from 'react'
import { cn } from '@/lib/utils'
import { TaskHistory } from '@/features/results/TaskHistory'
import { useTaskComments } from '../api'
import { CommentSection } from '../CommentSection'
import { SectionLabel } from './ui'

interface Props {
  taskId: string
  currentUserId: string
  userById: Map<string, { display_name: string }>
  nameOf: (id: string) => string
}

/** Comments (discussion) and the durable change history (audit log). */
export function ActivityBlock({ taskId, currentUserId, userById, nameOf }: Props) {
  const { data: comments = [] } = useTaskComments(taskId)
  const [tab, setTab] = useState<'comments' | 'history'>('comments')
  return (
    <div className="space-y-3">
      <SectionLabel>Activity</SectionLabel>
      <div className="flex gap-0 border-b">
        {(['comments', 'history'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium capitalize border-b-2 -mb-px transition-colors',
              tab === t ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground',
            )}
          >
            {t === 'comments' ? `Comments (${comments.length})` : 'History'}
          </button>
        ))}
      </div>
      {tab === 'comments' && <CommentSection taskId={taskId} currentUserId={currentUserId} userById={userById} />}
      {tab === 'history' && <TaskHistory taskId={taskId} nameOf={nameOf} />}
    </div>
  )
}
