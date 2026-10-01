import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const AUTH_COOKIE = 'quant_authed'

export function middleware(request: NextRequest) {
  const authed = request.cookies.has(AUTH_COOKIE)
  const { pathname } = request.nextUrl

  // 受保护路由：未登录则服务端直接重定向到 /login，避免客户端白屏
  if (pathname.startsWith('/recommendations') && !authed) {
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    url.search = ''
    return NextResponse.redirect(url)
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/recommendations/:path*'],
}
