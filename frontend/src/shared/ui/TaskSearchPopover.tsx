import { useState, useCallback, useRef } from 'react'
import { Search, X } from 'lucide-react'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useSearchTasks, type Task } from '@/features/tasks/api'
import { TaskTypeIcon, TYPE_COLORS } from '@/features/tasks/TaskTypeIcon'

const SYSTEM_TYPES = [
  { key: 'task',     label: 'Task' },
  { key: 'bug',      label: 'Bug' },
  { key: 'story',    label: 'Story' },
  { key: 'epic',     label: 'Epic' },
  { key: 'decision', label: 'Decision' },
] as const

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const update = useCallback((v: T) => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setDebounced(v), delay)
  }, [delay])
  // sync raw → debounced
  const rawRef = useRef(value)
  if (rawRef.current !== value) { rawRef.current = value; update(value) }
  return debounced
}

interface Props {
  onSelect: (task: Task) => void
  excludeIds?: Set<string>
  trigger: React.ReactNode
}

export function TaskSearchPopover({ onSelect, excludeIds, trigger }: Props) {
  const [open, setOpen]           = useState(false)
  const [query, setQuery]         = useState('')
  const [typeFilter, setTypeFilter] = useState<Set<string>>(new Set())

  const debouncedQ = useDebounced(query, 280)
  const activeTypes = [...typeFilter]
  const { data: results = [], isFetching } = useSearchTasks(debouncedQ, activeTypes)

  const filtered = results.filter(t => !excludeIds?.has(t.id))

  function toggleType(key: string) {
    setTypeFilter(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function handleSelect(task: Task) {
    onSelect(task)
    setOpen(false)
    setQuery('')
  }

  function handleOpenChange(v: boolean) {
    setOpen(v)
    if (!v) { setQuery(''); setTypeFilter(new Set()) }
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>{trigger}</PopoverTrigger>
      <PopoverContent
        className="w-[420px] p-0"
        align="start"
        side="bottom"
        sideOffset={6}
      >
        {/* Search input */}
        <div className="flex items-center gap-2 px-3 py-2 border-b">
          <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <Input
            autoFocus
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search by key or title…"
            className="h-7 border-0 shadow-none px-0 text-sm focus-visible:ring-0"
          />
          {query && (
            <button onClick={() => setQuery('')} className="text-muted-foreground hover:text-foreground">
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Type filter chips */}
        <div className="flex items-center gap-1.5 px-3 py-2 border-b flex-wrap">
          {SYSTEM_TYPES.map(({ key, label }) => {
            const active = typeFilter.has(key)
            const color  = TYPE_COLORS[key] ?? '#6366f1'
            return (
              <button
                key={key}
                onClick={() => toggleType(key)}
                className={cn(
                  'flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium border transition-colors',
                  active
                    ? 'border-transparent text-white'
                    : 'border-border text-muted-foreground hover:text-foreground hover:border-foreground/30',
                )}
                style={active ? { background: color } : undefined}
              >
                <TaskTypeIcon typeKey={key} color={active ? '#fff' : color} size={10} />
                {label}
              </button>
            )
          })}
          {typeFilter.size > 0 && (
            <button
              onClick={() => setTypeFilter(new Set())}
              className="text-[11px] text-muted-foreground hover:text-foreground ml-auto"
            >
              Clear
            </button>
          )}
        </div>

        {/* Results */}
        <div className="max-h-64 overflow-y-auto">
          {debouncedQ.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">
              Type to search tasks
            </p>
          ) : isFetching && filtered.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">Searching…</p>
          ) : filtered.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-6">No tasks found</p>
          ) : (
            filtered.map(task => (
              <button
                key={task.id}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-muted/40 transition-colors"
                onClick={() => handleSelect(task)}
              >
                <TaskTypeIcon
                  typeKey={task.task_type?.key ?? 'task'}
                  color={task.task_type?.color ?? TYPE_COLORS[task.task_type?.key ?? 'task'] ?? '#6366f1'}
                  size={13}
                />
                <span className="font-mono text-[11px] text-muted-foreground shrink-0">
                  {task.key}
                </span>
                <span className="text-xs truncate flex-1 text-foreground">{task.title}</span>
                {isFetching && (
                  <span className="w-1 h-1 rounded-full bg-muted-foreground/40 shrink-0 animate-pulse" />
                )}
              </button>
            ))
          )}
        </div>

        {filtered.length >= 50 && (
          <p className="text-[11px] text-muted-foreground text-center py-1.5 border-t">
            Showing first 50 results — narrow your search
          </p>
        )}
      </PopoverContent>
    </Popover>
  )
}
