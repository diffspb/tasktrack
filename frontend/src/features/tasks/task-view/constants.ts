import { ArrowDown, ArrowRight, ArrowUp, ChevronsUp, type LucideIcon } from 'lucide-react'

export const PRIORITY_CONFIG: Record<string, { Icon: LucideIcon; color: string }> = {
  low:      { Icon: ArrowDown,  color: 'oklch(0.65 0.08 240)' },
  medium:   { Icon: ArrowRight, color: 'oklch(0.55 0.14 200)' },
  high:     { Icon: ArrowUp,    color: 'oklch(0.60 0.18 55)'  },
  critical: { Icon: ChevronsUp, color: 'oklch(0.55 0.22 25)'  },
}

export const STATUS_DOT: Record<string, string> = {
  initial:      'oklch(0.6 0 0)',
  intermediate: 'oklch(0.55 0.14 230)',
  final:        'oklch(0.55 0.15 150)',
}

export const fmtDate = (s: string) =>
  new Date(s).toLocaleDateString('en', { day: 'numeric', month: 'short', year: 'numeric' })
