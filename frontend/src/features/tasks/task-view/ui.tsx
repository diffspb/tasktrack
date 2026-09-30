export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground/60 mb-2">
      {children}
    </p>
  )
}

export function Avatar({ name }: { name: string }) {
  return (
    <div className="h-7 w-7 rounded-full bg-muted-foreground/15 flex items-center justify-center text-[11px] font-bold shrink-0 select-none">
      {name.slice(0, 2).toUpperCase()}
    </div>
  )
}
