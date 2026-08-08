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
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setUser: (user) => set({ user }),
      logout: async () => {
        const { refreshToken } = get()
        set({ accessToken: null, refreshToken: null, user: null })
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
      onRehydrateStorage: () => () => {
        useAuthStore.setState({ hydrated: true })
      },
    },
  ),
)
