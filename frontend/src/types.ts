import type { ApiResponse } from './services/types'

export type { ApiResponse }

export interface DashboardData {
  total_signals: number
  buy_signals: number
  watch_signals: number
  last_scan: string | null
}

export interface ScreenResult {
  symbol: string
  name: string
  market: string
  score: number
  rs_rating: number
  eps_rating: number
  industry: string
  stage: string
  signal: string
  close_price: number
  volume_ratio: number
  near_high_pct: number
  sma50_pct: number
  sma150_pct: number
  sma200_pct: number
}

export interface WatchlistItem {
  id: number
  symbol: string
  market: string
  added_at: string
  note?: string
  current_price?: number
  change_pct?: number
}

export interface Signal {
  symbol: string
  signal: string
  reason: string
  date: string
}

export interface Position {
  symbol: string
  shares: number
  avg_price: number
  current_price: number
  pnl_pct: number
  market_value: number
}

export interface Order {
  id: number
  symbol: string
  side: string
  quantity: number
  price: number
  status: string
  created_at: string
}

export interface Trade {
  id: number
  symbol: string
  side: string
  quantity: number
  price: number
  pnl: number
  executed_at: string
}

export interface BacktestConfig {
  strategy: string
  symbols: string[]
  start_date: string
  end_date: string
  initial_capital: number
}

export interface BacktestResult {
  id: number
  total_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  trades: number
}

export interface Pattern {
  type: string
  direction: string
  reliability: string
  description: string
}

export interface Stock {
  symbol: string
  name: string
  market: string
  sector: string
  industry: string
  close_price: number
  change_pct: number
  volume: number
  volume_avg: number
  high_52w: number
  low_52w: number
  ma50: number
  ma150: number
  ma200: number
}

export interface AIReport {
  date: string
  summary: string
  recommendations: string[]
  risk_level: string
}
