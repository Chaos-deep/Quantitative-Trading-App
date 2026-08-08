import { ActionBadge } from '@/components/ActionBadge'
import { fmtDate, fmtShares } from '@/lib/format'
import type { PersonalAdvice } from '@/types'

interface Props {
  items: PersonalAdvice[]
}

export function PersonalAdviceTable({ items }: Props) {
  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 p-10 text-center text-sm text-slate-400">
        暂无建议，请先在我的持仓/偏好中添加持仓
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-4 py-3 font-medium">日期</th>
            <th className="px-4 py-3 font-medium">代码</th>
            <th className="px-4 py-3 font-medium">名称</th>
            <th className="px-4 py-3 font-medium">操作</th>
            <th className="px-4 py-3 font-medium">建议股数</th>
            <th className="px-4 py-3 font-medium">理由</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {items.map((a) => (
            <tr key={`${a.stock_code}-${a.advice_date}`} className="hover:bg-slate-50">
              <td className="px-4 py-3 whitespace-nowrap text-slate-600">{fmtDate(a.advice_date)}</td>
              <td className="px-4 py-3 font-mono text-slate-900">{a.stock_code}</td>
              <td className="px-4 py-3 text-slate-900">{a.stock_name ?? '—'}</td>
              <td className="px-4 py-3">
                <ActionBadge action={a.action} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-slate-600">
                {fmtShares(a.suggested_shares)}
              </td>
              <td className="max-w-md truncate px-4 py-3 text-slate-500">{a.reason ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
