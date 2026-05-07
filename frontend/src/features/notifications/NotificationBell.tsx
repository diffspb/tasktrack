import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/shared/api/client'
import { useNotifications, useMarkRead, useMarkAllRead, type Notification } from './api'

const EVENT_LABEL: Record<Notification['event_type'], string> = {
  task_assigned:      'Assigned',
  awaiting_decision:  'Awaiting Decision',
  revision_requested: 'Revision',
  decision_made:      'Decision',
  task_closed:        'Closed',
  decision_reminder:  'Reminder',
}

export function NotificationBell() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const { data } = useNotifications()
  const markRead = useMarkRead()
  const markAllRead = useMarkAllRead()

  useEffect(() => {
    if (!open) return
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const unread = data?.unread_count ?? 0
  const items = data?.items ?? []

  async function handleClick(n: Notification) {
    if (!n.is_read) await markRead.mutateAsync(n.id)
    if (n.task_id) {
      try {
        const task = await api.get(`/tasks/${n.task_id}`).then(r => r.data)
        navigate(`/tasks/${task.key}`)
      } catch {
        // Task no longer accessible — just close the popover.
      }
    }
    setOpen(false)
  }

  return (
    <div className="relative" ref={ref}>
      <Button
        size="icon"
        variant="ghost"
        className="relative h-8 w-8"
        onClick={() => setOpen(o => !o)}
        aria-label={`Notifications${unread > 0 ? ` (${unread} unread)` : ''}`}
      >
        <Bell className="h-4 w-4" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 h-4 min-w-4 rounded-full bg-destructive px-1 text-[10px] font-bold leading-4 text-white">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-[360px] rounded-lg border bg-background shadow-lg z-50 max-h-[480px] flex flex-col">
          <div className="flex items-center justify-between border-b px-3 py-2">
            <span className="text-sm font-semibold">Notifications</span>
            {unread > 0 && (
              <Button
                size="sm" variant="ghost" className="h-6 text-xs"
                onClick={() => markAllRead.mutate()}
                disabled={markAllRead.isPending}
              >
                <Check className="h-3 w-3 mr-1" /> Mark all read
              </Button>
            )}
          </div>
          <div className="overflow-y-auto flex-1">
            {items.length === 0 ? (
              <p className="p-6 text-center text-xs text-muted-foreground">No notifications.</p>
            ) : (
              <ul className="divide-y">
                {items.map(n => (
                  <li key={n.id}>
                    <button
                      onClick={() => handleClick(n)}
                      className={`w-full text-left px-3 py-2.5 hover:bg-muted/50 transition-colors ${
                        n.is_read ? '' : 'bg-primary/[0.03]'
                      }`}
                    >
                      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">
                        <span className="font-semibold">{EVENT_LABEL[n.event_type]}</span>
                        <span>·</span>
                        <span>{new Date(n.created_at).toLocaleString()}</span>
                        {!n.is_read && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />}
                      </div>
                      <p className="text-sm leading-snug line-clamp-2">{n.message}</p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

