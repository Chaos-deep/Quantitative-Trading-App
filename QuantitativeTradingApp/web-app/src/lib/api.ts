// 统一 API 客户端：token 注入 + 401 单飞刷新（refreshAttempted 语义，见 docs/appendices/frontend/state.md）
'use client'

import { useAuthStore } from '@/stores/authStore'
import { API_BASE } from '@/lib/config'

export class ApiError extends Error {
  status: number
  detail?: string

  constructor(status: number, message: string, detail?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

// 单飞刷新：并发 401 共享同一个刷新 Promise，防止刷新风暴
let refreshPromise: Promise<boolean> | null = null

function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise

  const refreshToken = useAuthStore.getState().refreshToken
  const p = (async () => {
    if (!refreshToken) return false
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!res.ok) return false
      const data = await res.json()
      useAuthStore.getState().setTokens(data.access_token, data.refresh_token)
      return true
    } catch {
      return false
    }
  })()
  refreshPromise = p
  p.then(
    () => {
      refreshPromise = null
    },
    () => {
      refreshPromise = null
    },
  )
  return p
}

function forceLogoutAndRedirect(): void {
  void useAuthStore.getState().logout()
  if (typeof window !== 'undefined') {
    window.location.href = '/login'
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retried = false,
): Promise<T> {
  const { accessToken, refreshToken } = useAuthStore.getState()

  const headers = new Headers(options.headers ?? {})
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  // 401 → 单飞刷新一次 → 重放原请求；刷新失败则登出并回登录页
  if (res.status === 401 && !retried && refreshToken) {
    const ok = await tryRefresh()
    if (ok) return apiFetch<T>(path, options, true)
    forceLogoutAndRedirect()
    throw new ApiError(401, '登录已过期，请重新登录')
  }

  const text = await res.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!res.ok) {
    let detail: string | undefined
    if (body && typeof body === 'object' && 'detail' in body) {
      const d = (body as { detail: unknown }).detail
      detail = typeof d === 'string' ? d : JSON.stringify(d)
    }
    throw new ApiError(res.status, `请求失败（${res.status}）`, detail)
  }
  return body as T
}
