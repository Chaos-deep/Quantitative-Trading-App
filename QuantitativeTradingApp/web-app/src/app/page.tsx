'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

import { useAuthStore } from '@/stores/authStore'

export default function Home() {
  const router = useRouter()
  const hydrated = useAuthStore((s) => s.hydrated)
  const accessToken = useAuthStore((s) => s.accessToken)

  useEffect(() => {
    if (!hydrated) return
    router.replace(accessToken ? '/recommendations' : '/login')
  }, [hydrated, accessToken, router])

  return null
}
