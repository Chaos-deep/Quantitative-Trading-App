import { redirect } from 'next/navigation'

export default function Home() {
  // 服务端直接重定向，避免客户端 hydrate 前白屏；已登录用户会在 /login 被再导向 /recommendations
  redirect('/login')
}
