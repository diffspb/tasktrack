import { useState, useEffect } from 'react'
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { api } from '@/shared/api/client'
import { cn } from '@/lib/utils'

interface User {
  id: string
  email: string
  display_name: string
}

interface Props {
  value: User | null
  onChange: (user: User | null) => void
  placeholder?: string
}

export function UserSearchCombobox({ value, onChange, placeholder = 'Search by name or email…' }: Props) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(query.trim()), 250)
    return () => clearTimeout(t)
  }, [query])

  const { data: results = [], isFetching } = useQuery<User[]>({
    queryKey: ['user-search', debouncedQ],
    queryFn: () => api.get('/users/search', { params: { q: debouncedQ } }).then(r => r.data),
    enabled: debouncedQ.length >= 1,
    staleTime: 30_000,
  })

  function select(user: User) {
    onChange(user)
    setOpen(false)
    setQuery('')
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        className={cn(
          'flex w-full items-center justify-between rounded-md border border-input bg-background px-3 h-8 text-xs',
          'hover:bg-muted transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          !value && 'text-muted-foreground',
        )}
        aria-expanded={open}
      >
        <span className="truncate">
          {value ? `${value.display_name} — ${value.email}` : placeholder}
        </span>
        <ChevronsUpDown className="ml-2 h-3.5 w-3.5 shrink-0 opacity-50" />
      </PopoverTrigger>

      <PopoverContent className="w-80 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Name or email…"
            value={query}
            onValueChange={setQuery}
            className="h-8 text-xs"
          />
          <CommandList>
            {isFetching && (
              <div className="flex items-center justify-center py-3">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            )}
            {!isFetching && debouncedQ && results.length === 0 && (
              <CommandEmpty className="text-xs py-4">No users found.</CommandEmpty>
            )}
            {!isFetching && results.length > 0 && (
              <CommandGroup>
                {results.map(user => (
                  <CommandItem
                    key={user.id}
                    value={user.id}
                    onSelect={() => select(user)}
                    className="text-xs cursor-pointer"
                  >
                    <Check
                      className={cn('mr-2 h-3.5 w-3.5 shrink-0', value?.id === user.id ? 'opacity-100' : 'opacity-0')}
                    />
                    <div className="flex flex-col min-w-0">
                      <span className="font-medium truncate">{user.display_name}</span>
                      <span className="text-muted-foreground truncate">{user.email}</span>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
            {!debouncedQ && (
              <div className="py-3 text-center text-xs text-muted-foreground">
                Start typing to search
              </div>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
