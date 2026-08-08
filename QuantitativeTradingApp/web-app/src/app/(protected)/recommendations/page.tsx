'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'

import { Filters, type GlobalFilters } from '@/components/Filters'
import { PersonalAdviceTable } from '@/components/PersonalAdviceTable'
import { PortfolioPanel } from '@/components/PortfolioPanel'
import { RecommendationsTable } from '@/components/RecommendationsTable'
import { apiFetch } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import type { Page, PersonalAdvice, Recommendation, StrategyMeta, User } from '@/types'

type Tab = 'global' | 'personal'

export default function RecommendationsPage() {
  const router = useRouter()
  const hydrated = useAuthStore((s) => s.hydrated)
  const accessToken = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const logout = useAuthStore((s) => s.logout)

  const [tab, setTab] = useState<Tab>('global')
  const [filters, setFilters] = useState<GlobalFilters>({ strategy: '', signal: '', date: '' })

  useEffect(() => {
    if (hydrated && !accessToken) router.replace('/login')
  }, [hydrated, accessToken, router])

  const query = useMemo(() => {
    const p = new URLSearchParams()
    if (filters.strategy) p.set('strategy', filters.strategy)
    if (filters.signal) p.set('signal', filters.signal)
    if (filters.date) p.set('date', filters.date)
    p.set('limit', '100')
    return p.toString()
  }, [filters])

  const authed = hydrated && !!accessToken

  useSWR<User>(authed ? '/auth/me' : null, () => apiFetch<User>('/auth/me'), {
    onSuccess: setUser,
  })

  const { data: strategies } = useSWR<StrategyMeta[]>(
    authed ? '/strategies' : null,
    () => apiFetch<StrategyMeta[]>('/strategies'),
  )

  const { data: globalData, isLoading: loadingGlobal } = useSWR<Page<Recommendation>>(
    authed && tab === 'global' ? ['/recommendations/global', query] : null,
    () => apiFetch<Page<Recommendation>>(`/recommendations/global?${query}`),
  )

  const { data: personalData, isLoading: loadingPersonal } = useSWR<Page<PersonalAdvice>>(
    authed && tab === 'personal' ? '/recommendations/personal?limit=100' : null,
    () => apiFetch<Page<PersonalAdvice>>('/recommendations/personal?limit=100'),
  )

  const strategyNames = useMemo(
    () => Object.fromEntries((strategies ?? []).map((s) => [s.name, s.display_name])),
    [strategies],
  )

  async function handleLogout() {
    await logout()
    router.replace('/login')
  }

  if (!hydrated) return null
  if (!accessToken) return null

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">推荐中心</h1>
          <p className="text-sm text-slate-400">{user ? `当前用户：${user.username}` : '加载中…'}</p>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
        >
          退出登录
        </button>
      </header>

      <div className="flex gap-1 rounded-lg bg-slate-200/70 p-1">
        {(
          [
            { key: 'global', label: '全局推荐' },
            { key: 'personal', label: '我的建议' },
          ] as Array<{ key: Tab; label: string }>
        ).map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded px-4 py-2 text-sm font-medium transition ${
              tab === t.key ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'global' && (
        <div className="space-y-4">
          <Filters strategies={strategies ?? []} filters={filters} onChange={(n) => setFilters((f) => ({ ...f, ...n }))} />
          {loadingGlobal && !globalData ? (
            <div className="py-10 text-center text-sm text-slate-400">加载中…</div>
          ) : (
            <RecommendationsTable items={globalData?.items ?? []} strategyNames={strategyNames} />
          )}
        </div>
      )}

      {tab === 'personal' && (
        <div className="space-y-4">
          {loadingPersonal && !personalData ? (
            <div className="py-10 text-center text-sm text-slate-400">加载中…</div>
          ) : (
            <PersonalAdviceTable items={personalData?.items ?? []} />
          )}
        </div>
      )}

      <PortfolioPanel />
    </div>
  )
}
