'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

import { apiFetch, ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import type { TokenResponse, User } from '@/types'

type Mode = 'login' | 'register'

export default function LoginPage() {
  const router = useRouter()
  const hydrated = useAuthStore((s) => s.hydrated)
  const accessToken = useAuthStore((s) => s.accessToken)
  const setTokens = useAuthStore((s) => s.setTokens)
  const setUser = useAuthStore((s) => s.setUser)

  const [mode, setMode] = useState<Mode>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (hydrated && accessToken) router.replace('/recommendations')
  }, [hydrated, accessToken, router])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setInfo(null)
    if (!username.trim() || !password) {
      setError('请输入用户名和密码')
      return
    }
    setBusy(true)
    try {
      if (mode === 'register') {
        await apiFetch<User>('/auth/register', {
          method: 'POST',
          body: JSON.stringify({ username: username.trim(), password }),
        })
        setMode('login')
        setPassword('')
        setInfo('注册成功，请登录')
      } else {
        const tokens = await apiFetch<TokenResponse>('/auth/login', {
          method: 'POST',
          body: JSON.stringify({ username: username.trim(), password }),
        })
        setTokens(tokens.access_token, tokens.refresh_token)
        const me = await apiFetch<User>('/auth/me')
        setUser(me)
        router.replace('/recommendations')
      }
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : undefined
      setError(detail ?? '操作失败，请稍后再试')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-xl font-semibold text-slate-800">A股量化选股系统</h1>
        <p className="mb-6 text-sm text-slate-400">海龟 + 布林带双策略，个性化投顾</p>

        {error && (
          <div className="mb-4 rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>
        )}
        {info && (
          <div className="mb-4 rounded bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{info}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            placeholder="用户名（≥3 字符）"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
            type="password"
            placeholder="密码（≥6 位）"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
          />
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            {busy ? '处理中…' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          {mode === 'login' ? '还没有账号？' : '已有账号？'}
          <button
            type="button"
            className="ml-1 font-medium text-blue-600 hover:underline"
            onClick={() => {
              setMode(mode === 'login' ? 'register' : 'login')
              setError(null)
              setInfo(null)
            }}
          >
            {mode === 'login' ? '立即注册' : '去登录'}
          </button>
        </p>
      </div>
    </div>
  )
}
