import { useState, useRef, useEffect } from 'react'
import { Pencil, Trash2, Check, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { useTaskComments, useCreateComment, useUpdateComment, useDeleteComment, type Comment } from './api'

interface Props {
  taskId: string
  currentUserId: string
  userById: Map<string, { display_name: string }>
}

export function CommentSection({ taskId, currentUserId, userById }: Props) {
  const { data: comments = [], isLoading } = useTaskComments(taskId)
  const createComment = useCreateComment(taskId)

  const visible = comments.filter(c => !c.deleted_at)

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        Comments ({visible.length})
      </p>

      {visible.length > 0 && (
        <ul className="space-y-3">
          {visible.map(c => (
            <CommentItem
              key={c.id}
              comment={c}
              taskId={taskId}
              currentUserId={currentUserId}
              authorName={userById.get(c.author_id)?.display_name ?? c.author_id.slice(0, 8)}
            />
          ))}
        </ul>
      )}

      <CommentForm
        onSubmit={content => createComment.mutateAsync({ content })}
        isPending={createComment.isPending}
        currentUserId={currentUserId}
        userById={userById}
      />
    </div>
  )
}

function CommentItem({ comment, taskId, currentUserId, authorName }: {
  comment: Comment
  taskId: string
  currentUserId: string
  authorName: string
}) {
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState(comment.content)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const updateComment = useUpdateComment(taskId)
  const deleteComment = useDeleteComment(taskId)

  useEffect(() => {
    if (editing && textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.selectionStart = textareaRef.current.value.length
    }
  }, [editing])

  const isOwn = comment.author_id === currentUserId
  const initials = authorName.slice(0, 2).toUpperCase()

  async function handleSaveEdit() {
    const trimmed = editContent.trim()
    if (!trimmed || trimmed === comment.content) {
      setEditing(false)
      setEditContent(comment.content)
      return
    }
    await updateComment.mutateAsync({ commentId: comment.id, content: trimmed })
    setEditing(false)
  }

  function handleCancelEdit() {
    setEditing(false)
    setEditContent(comment.content)
  }

  return (
    <li className="group flex gap-3">
      {/* Avatar */}
      <div className="h-7 w-7 rounded-full bg-muted-foreground/20 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
        {initials}
      </div>

      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium">{authorName}</span>
          <span className="text-[11px] text-muted-foreground">
            {formatRelative(comment.created_at)}
          </span>
          {comment.edited_at && (
            <span className="text-[10px] text-muted-foreground/50 italic">edited</span>
          )}
          {comment.labels.length > 0 && (
            <div className="flex gap-1">
              {comment.labels.map(l => (
                <span key={l} className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                  {l}
                </span>
              ))}
            </div>
          )}
          <div className="flex-1" />
          {/* Actions — own comments only */}
          {isOwn && !editing && (
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={() => setEditing(true)}
                className="rounded p-1 text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted transition-colors"
                title="Edit"
              >
                <Pencil className="h-3 w-3" />
              </button>
              <button
                onClick={() => deleteComment.mutateAsync(comment.id)}
                disabled={deleteComment.isPending}
                className="rounded p-1 text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors"
                title="Delete"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          )}
        </div>

        {/* Content */}
        {editing ? (
          <div className="mt-1.5 space-y-2">
            <textarea
              ref={textareaRef}
              value={editContent}
              onChange={e => setEditContent(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Escape') handleCancelEdit()
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSaveEdit()
              }}
              rows={3}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-ring resize-none"
            />
            <div className="flex gap-1.5">
              <Button
                size="sm" variant="outline" className="h-6 px-2 text-xs gap-1"
                disabled={updateComment.isPending}
                onClick={handleSaveEdit}
              >
                <Check className="h-3 w-3" /> Save
              </Button>
              <Button
                size="sm" variant="ghost" className="h-6 px-2 text-xs gap-1"
                onClick={handleCancelEdit}
              >
                <X className="h-3 w-3" /> Cancel
              </Button>
            </div>
          </div>
        ) : (
          <p className="mt-0.5 text-sm text-foreground/90 whitespace-pre-wrap leading-relaxed">
            {comment.content}
          </p>
        )}
      </div>
    </li>
  )
}

function CommentForm({ onSubmit, isPending, currentUserId, userById }: {
  onSubmit: (content: string) => Promise<unknown>
  isPending: boolean
  currentUserId: string
  userById: Map<string, { display_name: string }>
}) {
  const [content, setContent] = useState('')
  const [focused, setFocused] = useState(false)
  const authorName = userById.get(currentUserId)?.display_name ?? 'You'
  const initials = authorName.slice(0, 2).toUpperCase()

  async function handleSubmit() {
    const trimmed = content.trim()
    if (!trimmed) return
    await onSubmit(trimmed)
    setContent('')
    setFocused(false)
  }

  return (
    <div className="flex gap-3">
      <div className="h-7 w-7 rounded-full bg-primary/20 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5 text-primary">
        {initials}
      </div>
      <div className="flex-1 space-y-2">
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          onFocus={() => setFocused(true)}
          onKeyDown={e => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit()
            if (e.key === 'Escape') { setContent(''); setFocused(false) }
          }}
          placeholder="Add a comment… (Ctrl+Enter to submit)"
          rows={focused ? 3 : 1}
          className={cn(
            'w-full rounded-md border border-input bg-background px-3 py-2 text-sm outline-none resize-none transition-all',
            'focus:ring-1 focus:ring-ring',
            focused ? 'border-ring/50' : '',
          )}
        />
        {focused && (
          <div className="flex gap-1.5">
            <Button
              size="sm" className="h-6 px-2.5 text-xs"
              disabled={!content.trim() || isPending}
              onClick={handleSubmit}
            >
              {isPending ? 'Saving…' : 'Comment'}
            </Button>
            <Button
              size="sm" variant="ghost" className="h-6 px-2 text-xs"
              onClick={() => { setContent(''); setFocused(false) }}
            >
              Cancel
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

function formatRelative(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return d.toLocaleDateString('en', { day: 'numeric', month: 'short' })
}
