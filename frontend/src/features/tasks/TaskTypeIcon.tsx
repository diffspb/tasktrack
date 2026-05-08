import { Bug, BookOpen, Layers, Scale, CheckSquare2 } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

const TYPE_ICONS: Record<string, LucideIcon> = {
  bug:      Bug,
  story:    BookOpen,
  epic:     Layers,
  decision: Scale,
  task:     CheckSquare2,
}

export const TYPE_COLORS: Record<string, string> = {
  bug:      '#ef4444',
  story:    '#10b981',
  epic:     '#f59e0b',
  decision: '#8b5cf6',
  task:     '#6366f1',
}

interface Props {
  typeKey: string
  color?: string | null
  size?: number
  className?: string
}

export function TaskTypeIcon({ typeKey, color, size = 14, className }: Props) {
  const Icon = TYPE_ICONS[typeKey] ?? TYPE_ICONS.task
  const iconColor = color ?? TYPE_COLORS[typeKey] ?? TYPE_COLORS.task
  return <Icon size={size} className={cn('shrink-0', className)} style={{ color: iconColor }} />
}
