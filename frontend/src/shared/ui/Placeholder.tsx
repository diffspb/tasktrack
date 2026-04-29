import { Construction } from 'lucide-react'

interface Props {
  title: string
  phase: number
}

export function Placeholder({ title, phase }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24 text-center text-muted-foreground">
      <Construction className="h-10 w-10 opacity-30" />
      <p className="font-medium">{title}</p>
      <p className="text-sm">Coming in Phase {phase}</p>
    </div>
  )
}
