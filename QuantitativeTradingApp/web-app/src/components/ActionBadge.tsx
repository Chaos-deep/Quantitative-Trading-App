import type { Action } from '@/types'

const labels: Record<Action, string> = {
  BUY: '买入',
  SELL: '卖出',
  HOLD: '持有',
}

const styles: Record<Action, string> = {
  BUY: 'bg-emerald-100 text-emerald-700',
  SELL: 'bg-rose-100 text-rose-700',
  HOLD: 'bg-slate-100 text-slate-600',
}

export function ActionBadge({ action }: { action: Action }) {
  return (
    <span
      className={`inline-flex rounded px-2 py-0.5 text-xs font-semibold ${
        styles[action] ?? 'bg-slate-100 text-slate-600'
      }`}
    >
      {labels[action] ?? action}
    </span>
  )
}
