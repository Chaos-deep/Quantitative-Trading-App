import { SignalBadge } from '@/components/SignalBadge'
import { fmtNumber, fmtScore } from '@/lib/format'
import type { Recommendation } from '@/types'

interface Props {
  items: Recommendation[]
  strategyNames?: Record<string, string>
}

export function RecommendationsTable({ items, strategyNames }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-400">
        暂无推荐数据（可能尚未运行流水线，请稍后再试）
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">策略</th>
            <th className="px-4 py-3 font-medium">代码</th>
            <th className="px-4 py-3 font-medium">名称</th>
            <th className="px-4 py-3 font-medium">信号</th>
            <th className="px-4 py-3 font-medium">评分</th>
            <th className="px-4 py-3 font-medium">收盘价</th>
            <th className="px-4 py-3 font-medium">原因</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((r) => (
            <tr key={`${r.strategy}-${r.stock_code}`} className="hover:bg-slate-50">
              <td className="px-4 py-3 whitespace-nowrap text-slate-600">
                {strategyNames?.[r.strategy] ?? r.strategy}
              </td>
              <td className="px-4 py-3 font-mono text-slate-900">{r.stock_code}</td>
              <td className="px-4 py-3 text-slate-900">{r.stock_name ?? '—'}</td>
              <td className="px-4 py-3">
                <SignalBadge signal={r.signal} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-slate-600">
                {fmtScore(r.score)}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-slate-600">
                {fmtNumber(r.close)}
              </td>
              <td className="max-w-md truncate px-4 py-3 text-slate-500">{r.reason ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
