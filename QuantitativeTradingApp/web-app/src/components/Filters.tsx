import type { Signal, StrategyMeta } from '@/types'

export interface GlobalFilters {
  strategy: string
  signal: string
  date: string
}

interface Props {
  strategies: StrategyMeta[]
  filters: GlobalFilters
  onChange: (next: Partial<GlobalFilters>) => void
}

const signalOptions: Array<{ value: string; label: string }> = [
  { value: '', label: '全部信号' },
  { value: 'BUY', label: 'BUY' },
  { value: 'HOLD', label: 'HOLD' },
  { value: 'AVOID', label: 'AVOID' },
]

export function Filters({ strategies, filters, onChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label className="flex items-center gap-2 text-sm text-slate-600">
        策略
        <select
          className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          value={filters.strategy}
          onChange={(e) => onChange({ strategy: e.target.value })}
        >
          <option value="">全部策略</option>
          {strategies.map((s) => (
            <option key={s.name} value={s.name}>
              {s.display_name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm text-slate-600">
        信号
        <select
          className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          value={filters.signal}
          onChange={(e) => onChange({ signal: e.target.value })}
        >
          {signalOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex items-center gap-2 text-sm text-slate-600">
        日期
        <input
          type="date"
          className="rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
          value={filters.date}
          onChange={(e) => onChange({ date: e.target.value })}
        />
      </label>
    </div>
  )
}
