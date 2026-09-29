import { cn } from '@/lib/utils'

export function SectionLabel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <p className={cn('text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60 mb-2', className)}>
      {children}
    </p>
  )
}

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger' | 'muted'

const TONE: Record<Tone, string> = {
  neutral: 'bg-muted text-foreground',
  info:    'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  success: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  warning: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  danger:  'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  muted:   'bg-muted text-muted-foreground',
}

export function Pill({ tone = 'neutral', children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span className={cn('inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap', TONE[tone])}>
      {children}
    </span>
  )
}

const STATE: Record<string, [Tone, string]> = {
  // task result_state
  none:              ['muted', 'No result'],
  proposed:          ['info', 'Awaiting review'],
  changes_requested: ['warning', 'Changes requested'],
  accepted:          ['success', 'Accepted'],
  rejected:          ['danger', 'Rejected'],
  historical:        ['muted', 'Historical, not reviewed'],
  // proposal status
  submitted:         ['info', 'Submitted'],
  withdrawn:         ['muted', 'Withdrawn'],
  superseded:        ['muted', 'Superseded'],
  // work package state
  draft:             ['warning', 'Draft'],
  issued:            ['success', 'Issued'],
  draft_changed:     ['warning', 'Changed since issue'],
  // session state
  active:            ['info', 'Active'],
  completed:         ['success', 'Completed'],
  released:          ['muted', 'Released'],
}

export function StateBadge({ state }: { state: string }) {
  const [tone, label] = STATE[state] ?? ['neutral', state]
  return <Pill tone={tone}>{label}</Pill>
}
