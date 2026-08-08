'use client'

export default function ErrorBoundary({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-sm text-slate-600">
      <p>页面加载出错：{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
      >
        重试
      </button>
    </div>
  )
}
