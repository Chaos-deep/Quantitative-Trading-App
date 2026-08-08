import type { Metadata } from 'next'

import './globals.css'

export const metadata: Metadata = {
  title: 'A股量化选股系统',
  description: '海龟 + 布林带双策略 A 股量化选股与个性化投顾',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">{children}</body>
    </html>
  )
}
