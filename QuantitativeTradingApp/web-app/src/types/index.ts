// 与后端 app/schemas/schemas.py 对齐的 API 类型

export interface User {
  id: number
  username: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export type Signal = 'BUY' | 'HOLD' | 'AVOID'
export type Action = 'BUY' | 'SELL' | 'HOLD'

export interface Recommendation {
  stock_code: string
  stock_name: string | null
  strategy: string
  run_date: string
  signal: Signal
  score: number
  close: number | null
  reason: string | null
}

export interface PersonalAdvice {
  stock_code: string
  stock_name: string | null
  advice_date: string
  action: Action
  suggested_shares: number
  close: number | null
  reason: string | null
  strategy_signals: Array<Record<string, unknown>> | null
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  limit: number
}

export interface StockItem {
  code: string
  name: string
  market: string | null
}

export interface BarItem {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number | null
}

export interface StrategyMeta {
  name: string
  display_name: string
  description: string
}

export interface PositionPayload {
  stock_code: string
  shares: number
  cost_price: number | null
  buy_date: string | null
}

export interface Position {
  id: number
  user_id: number
  stock_code: string
  shares: number
  cost_price: number | null
  buy_date: string | null
}

export type RiskLevel = 'aggressive' | 'moderate' | 'conservative'

export interface Preferences {
  user_id: number
  risk_level: RiskLevel
  total_capital: number | null
  updated_at: string
}
