import type { Signal } from '@/types'

const styles: Record<Signal, string> = {
  BUY: 'bg-emerald-100 text-emerald-700',
  HOLD: 'bg-amber-100 text-amber-700',
  AVOID: 'bg-rose-100 text-rose-700',
}

export function SignalBadge({ signal }: { signal: Signal }) {
  return (
    <span
      className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ${
        styles[signal] ?? 'bg-slate-100 text-slate-600'
      }`}
    >
      {signal}
    </span>
  )
}
