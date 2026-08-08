import { API_BASE } from '@/lib/config'

export function fmtNumber(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined) return '—'
  return v.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function fmtScore(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return v.toFixed(1)
}

export function fmtShares(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return v.toLocaleString('zh-CN')
}

export function fmtDate(d: string | null | undefined): string {
  return d ?? '—'
}
