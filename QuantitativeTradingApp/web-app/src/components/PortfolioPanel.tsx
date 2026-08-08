'use client'

import { useCallback, useEffect, useState } from 'react'
import useSWR from 'swr'

import { apiFetch, ApiError } from '@/lib/api'
import { fmtNumber } from '@/lib/format'
import type { Preferences, RiskLevel, StockItem } from '@/types'

const riskOptions: Array<{ value: RiskLevel; label: string }> = [
  { value: 'conservative', label: '保守' },
  { value: 'moderate', label: '稳健' },
  { value: 'aggressive', label: '激进' },
]

const prefsFetcher = () => apiFetch<Preferences>('/preferences')

export function PortfolioPanel() {
  const { data: prefs, mutate: reloadPrefs } = useSWR('/preferences', prefsFetcher)

  // ---- 持仓录入 ----
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<StockItem[]>([])
  const [selected, setSelected] = useState<StockItem | null>(null)
  const [shares, setShares] = useState('')
  const [costPrice, setCostPrice] = useState('')
  const [buyDate, setBuyDate] = useState('')

  // ---- 偏好 ----
  const [riskLevel, setRiskLevel] = useState<RiskLevel>('moderate')
  const [totalCapital, setTotalCapital] = useState('')

  const [message, setMessage] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    if (prefs) {
      setRiskLevel(prefs.risk_level)
      setTotalCapital(prefs.total_capital != null ? String(prefs.total_capital) : '')
    }
  }, [prefs])

  // 搜索股票（防抖 300ms）
  useEffect(() => {
    if (!query.trim() || selected) {
      setSuggestions([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const res = await apiFetch<StockItem[]>(
          `/stocks/search?q=${encodeURIComponent(query.trim())}&limit=8`,
        )
        setSuggestions(res)
      } catch {
        setSuggestions([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query, selected])

  const submitPosition = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      if (!selected) {
        setMessage({ type: 'err', text: '请先从搜索结果中选择股票' })
        return
      }
      const n = Number(shares)
      if (!Number.isInteger(n) || n <= 0) {
        setMessage({ type: 'err', text: '股数必须为正整数（1 手 = 100 股）' })
        return
      }
      try {
        await apiFetch('/positions', {
          method: 'POST',
          body: JSON.stringify({
            stock_code: selected.code,
            shares: n,
            cost_price: costPrice ? Number(costPrice) : null,
            buy_date: buyDate || null,
          }),
        })
        setMessage({ type: 'ok', text: `已保存持仓：${selected.code} ${selected.name}` })
        setSelected(null)
        setQuery('')
        setShares('')
        setCostPrice('')
        setBuyDate('')
        setSuggestions([])
      } catch (err) {
        const detail = err instanceof ApiError ? err.detail : undefined
        setMessage({ type: 'err', text: `保存失败：${detail ?? '请稍后再试'}` })
      }
    },
    [selected, shares, costPrice, buyDate],
  )

  const submitPreferences = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      try {
        await apiFetch('/preferences', {
          method: 'PUT',
          body: JSON.stringify({
            risk_level: riskLevel,
            total_capital: totalCapital ? Number(totalCapital) : null,
          }),
        })
        await reloadPrefs()
        setMessage({ type: 'ok', text: '偏好已保存' })
      } catch (err) {
        const detail = err instanceof ApiError ? err.detail : undefined
        setMessage({ type: 'err', text: `保存失败：${detail ?? '请稍后再试'}` })
      }
    },
    [riskLevel, totalCapital, reloadPrefs],
  )

  const selectStock = (s: StockItem) => {
    setSelected(s)
    setQuery(s.code + ' ' + s.name)
    setSuggestions([])
  }

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="text-base font-semibold text-slate-800">我的持仓 / 偏好</h2>

      {message && (
        <div
          className={`rounded px-3 py-2 text-sm ${
            message.type === 'ok' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {/* 持仓录入 */}
        <form onSubmit={submitPosition} className="space-y-3">
          <h3 className="text-sm font-medium text-slate-700">新增 / 更新持仓</h3>

          <div className="relative">
            <input
              className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
              placeholder="搜索股票代码或名称"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value)
                setSelected(null)
              }}
            />
            {suggestions.length > 0 && (
              <ul className="absolute z-10 mt-1 w-full overflow-hidden rounded border border-slate-200 bg-white shadow">
                {suggestions.map((s) => (
                  <li key={s.code}>
                    <button
                      type="button"
                      className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50"
                      onClick={() => selectStock(s)}
                    >
                      <span className="font-mono text-slate-800">{s.code}</span>
                      <span className="text-slate-500">{s.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <input
            className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            type="number"
            min={100}
            step={100}
            placeholder="股数（1 手 = 100 股）"
            value={shares}
            onChange={(e) => setShares(e.target.value)}
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              className="rounded border border-slate-300 px-2 py-1.5 text-sm"
              type="number"
              min={0}
              step="0.01"
              placeholder="成本价（元）"
              value={costPrice}
              onChange={(e) => setCostPrice(e.target.value)}
            />
            <input
              className="rounded border border-slate-300 px-2 py-1.5 text-sm"
              type="date"
              value={buyDate}
              onChange={(e) => setBuyDate(e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            保存持仓
          </button>
        </form>

        {/* 偏好 */}
        <form onSubmit={submitPreferences} className="space-y-3">
          <h3 className="text-sm font-medium text-slate-700">风险偏好与总资金</h3>

          <select
            className="w-full rounded border border-slate-300 bg-white px-2 py-1.5 text-sm"
            value={riskLevel}
            onChange={(e) => setRiskLevel(e.target.value as RiskLevel)}
          >
            {riskOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          <input
            className="w-full rounded border border-slate-300 px-2 py-1.5 text-sm"
            type="number"
            min={0}
            step="1000"
            placeholder={`总资金（元），当前：${fmtNumber(prefs?.total_capital ?? null, 0)}`}
            value={totalCapital}
            onChange={(e) => setTotalCapital(e.target.value)}
          />

          <button
            type="submit"
            className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            保存偏好
          </button>
        </form>
      </div>
    </section>
  )
}
