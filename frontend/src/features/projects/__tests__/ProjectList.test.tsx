import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { TooltipProvider } from '@/components/ui/tooltip'
import { AuthProvider } from '@/features/auth/AuthProvider'
import { ProjectList } from '../ProjectList'
import * as api from '../api'

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <TooltipProvider>
          <MemoryRouter>{children}</MemoryRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

describe('ProjectList', () => {
  it('shows loading skeletons while fetching', () => {
    vi.spyOn(api, 'useProjects').mockReturnValue({
      data: undefined, isLoading: true, isError: false,
    } as unknown as ReturnType<typeof api.useProjects>)

    render(<ProjectList />, { wrapper })
    expect(screen.getByText('Projects')).toBeInTheDocument()
  })

  it('renders project cards', () => {
    vi.spyOn(api, 'useProjects').mockReturnValue({
      data: [
        {
          id: '1', name: 'Alpha', key: 'ALP', description: null,
          visibility: 'public', is_archived: false, version: 1,
          members: [{ user_id: 'u1', role: 'admin' }], created_at: '2026-01-01',
        },
        {
          id: '2', name: 'Beta', key: 'BET', description: 'Second project',
          visibility: 'restricted', is_archived: false, version: 1,
          members: [], created_at: '2026-01-02',
        },
      ],
      isLoading: false, isError: false,
    } as unknown as ReturnType<typeof api.useProjects>)

    render(<ProjectList />, { wrapper })
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText('Beta')).toBeInTheDocument()
    expect(screen.getByText('Second project')).toBeInTheDocument()
    expect(screen.getByText('1 member')).toBeInTheDocument()
  })

  it('shows empty state when no projects', () => {
    vi.spyOn(api, 'useProjects').mockReturnValue({
      data: [], isLoading: false, isError: false,
    } as unknown as ReturnType<typeof api.useProjects>)

    render(<ProjectList />, { wrapper })
    expect(screen.getByText('No projects yet.')).toBeInTheDocument()
  })

  it('shows error message on API failure', () => {
    vi.spyOn(api, 'useProjects').mockReturnValue({
      data: undefined, isLoading: false, isError: true,
    } as unknown as ReturnType<typeof api.useProjects>)

    render(<ProjectList />, { wrapper })
    expect(screen.getByText(/Failed to load projects/)).toBeInTheDocument()
  })
})
