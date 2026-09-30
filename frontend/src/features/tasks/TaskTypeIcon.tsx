import { ArrowRightLeft, Bug, BookOpen, CheckSquare2, FlaskConical, Layers, PlayCircle, Scale } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TYPE_COLORS } from './taskTypeColors'

const TYPE_ICONS: Record<string, LucideIcon> = {
  bug:      Bug,
  story:    BookOpen,
  epic:     Layers,
  decision: Scale,
  task:     CheckSquare2,
  // process types (ADR-023)
  execution: PlayCircle,
  research:  FlaskConical,
  migration: ArrowRightLeft,
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
