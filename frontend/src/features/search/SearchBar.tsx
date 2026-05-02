import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/shared/api/client'

interface SearchHit {
  id: string
  key: string
  title: string
  current_status_id: string
  project: { id: string; key: string; name: string }
  highlight: string
}

export function SearchBar() {
  const [q, setQ] = useState('')
  const [debounced, setDebounced] = useState('')
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(q.trim()), 200)
    return () => clearTimeout(t)
  }, [q])

  useEffect(() => {
    if (!open) return
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const { data, isFetching } = useQuery<{ items: SearchHit[] }>({
    queryKey: ['search', debounced],
    queryFn: () =>
      api.get(`/search?q=${encodeURIComponent(debounced)}&limit=10`).then(r => r.data),
    enabled: debounced.length > 0,
  })

  const items = data?.items ?? []

  function handlePick(hit: SearchHit) {
    setOpen(false)
    setQ('')
    navigate(`/tasks/${hit.key}`)
  }

  return (
    <div className="relative w-72" ref={ref}>
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <input
          type="search"
          value={q}
          onChange={e => { setQ(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          placeholder="Search tasks…"
          className="w-full rounded-md border border-input bg-background py-1 pl-7 pr-2 text-sm outline-none focus:ring-1 focus:ring-ring"
        />
      </div>

      {open && debounced.length > 0 && (
        <div className="absolute right-0 top-full mt-1 w-[420px] rounded-lg border bg-background shadow-lg z-50 max-h-[420px] overflow-y-auto">
          {isFetching && items.length === 0 && (
            <p className="p-4 text-xs text-center text-muted-foreground">Searching…</p>
          )}
          {!isFetching && items.length === 0 && (
            <p className="p-4 text-xs text-center text-muted-foreground">No matches.</p>
          )}
          {items.length > 0 && (
            <ul className="divide-y">
              {items.map(hit => (
                <li key={hit.id}>
                  <button
                    onClick={() => handlePick(hit)}
                    className="w-full flex flex-col gap-1 text-left px-3 py-2 hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] text-muted-foreground">{hit.project.key}/{hit.key}</span>
                      <span className="font-medium text-sm flex-1 truncate">{hit.title}</span>
                    </div>
                    <p
                      className="text-xs text-muted-foreground line-clamp-2 [&_b]:text-foreground [&_b]:font-semibold"
                      dangerouslySetInnerHTML={{ __html: hit.highlight }}
                    />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
