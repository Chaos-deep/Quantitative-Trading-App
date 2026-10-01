// auth store：access/refresh token + user，persist 到 localStorage（键 quant-auth）
'use client'

import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

import { API_BASE } from '@/lib/config'
import type { User } from '@/types'

interface AuthState {
  hydrated: boolean
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  setTokens: (accessToken: string, refreshToken: string) => void
  setUser: (user: User) => void
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      hydrated: false,
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (accessToken, refreshToken) => {
        set({ accessToken, refreshToken })
        if (typeof document !== 'undefined') {
          document.cookie = 'quant_authed=1; path=/; max-age=604800; SameSite=Lax'
        }
      },
      setUser: (user) => set({ user }),
      logout: async () => {
        const { refreshToken } = get()
        set({ accessToken: null, refreshToken: null, user: null })
        if (typeof document !== 'undefined') {
          document.cookie = 'quant_authed=1; path=/; max-age=0; SameSite=Lax'
        }
        if (refreshToken) {
          try {
            // 服务端吊销 refresh token（写黑名单）；失败无碍（幂等）
            await fetch(`${API_BASE}/auth/logout`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ refresh_token: refreshToken }),
            })
          } catch {
            // 忽略网络错误
          }
        }
      },
    }),
    {
      name: 'quant-auth',
      storage: createJSONStorage(() => localStorage),
      // 仅持久化凭证与用户；hydrated 是运行时状态，不应写入存储
      partialize: (s) => ({
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
        user: s.user,
      }),
    },
  ),
)

function markHydrated(): void {
  if (!useAuthStore.getState().hydrated) {
    useAuthStore.setState({ hydrated: true })
  }
}

// 水合完成回调必须在 store 创建之后注册：
// localStorage 为同步存储，水合可能在 create() 期间就已完成，
// 用 onRehydrateStorage 内部自引用 useAuthStore 会因初始化时序而失效。
// 注意：服务端（SSR/预渲染）无 localStorage，persist API 不会挂载，需守卫。
if (typeof window !== 'undefined' && useAuthStore.persist) {
  useAuthStore.persist.onFinishHydration(markHydrated)
  if (useAuthStore.persist.hasHydrated()) {
    markHydrated()
  }
}
