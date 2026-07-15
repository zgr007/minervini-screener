// === API Response Types ===

export interface ApiResponse<T> {
  data: T
  meta?: {
    page?: number
    limit?: number
    total?: number
  }
}

export interface ApiError {
  error: {
    code: string
    message: string
    details?: Record<string, unknown>
  }
}

// === Stock Types ===

export interface Stock {
  id: number
  symbol: string
  name: string
  exchange: string
  market: string
  sector: string | null
  industry: string | null
  market_cap: number | null
  currency: string
  is_active: boolean
}

export interface PatternDetail {
  detected: boolean
  first_bottom: number | null
  second_bottom: number | null
  neckline: number | null
  buy_point: number | null
  stop_price: number | null
  target_price: number | null
  confidence: string
  reason: string
  type: string
}

export interface BreakoutInfo {
  detected: boolean
  breakout_date: string | null
  breakout_price: number | null
  volume_ratio: number | null
  close_above_buy_point: boolean | null
  days_since_breakout: number | null
  follow_through: boolean | null
  pullback_to_buy_point: boolean | null
  failed_breakout: boolean | null
  reason: string
}

export interface StopLossInfo {
  stop_price: number | null
  stop_pct: number | null
  method: string
  atr_value: number | null
  risk_amount: number | null
  support_level: number | null
  trailing_active: boolean
  warning: string
}

export interface StockPriceData {
  code: string
  count: number
  prices: Record<string, { open: number; high: number; low: number; close: number; volume: number }>
}

export interface StockDetailData {
  code: string
  signal: string
  score: number
  stage2: boolean
  rs_rating: number
  rs_rank: number
  pattern: string
  pattern_detail: PatternDetail | null
  breakout: BreakoutInfo | null
  stop_loss: StopLossInfo | null
  reason: string
  current_price: number
}

export interface DailyBar {
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  adj_close: number
}

// === Screening Types ===

export interface ScreenResult {
  symbol: string
  name?: string
  run_date: string
  trend_passed: boolean
  rs_passed: boolean
  rs_rating?: number
  signal?: string
  total_score: number
  pattern_type?: string | null
  is_selected: boolean
  reason?: {
    stage2: FilterDetail
    rs: FilterDetail
    fundamental: FilterDetail
    institutional: FilterDetail
  }
}

export interface FilterDetail {
  passed: boolean
  score: number
  reason: string
}

// === Pattern Types ===

export interface Pattern {
  id: number
  symbol: string
  detected_date: string
  pattern_type: 'VCP' | 'CUP' | 'FLAT_BASE' | 'DOUBLE_BOTTOM' | 'BOLLINGER'
  pivot_price: number | null
  pattern_low: number | null
  stop_price: number | null
  target_price: number | null
  confidence: number | null
  status: string
  details: Record<string, unknown> | null
}

// === Watchlist Types ===

export interface WatchlistItem {
  id: number
  symbol: string
  added_date: string
  source: string | null
  pivot_price: number | null
  stop_price: number | null
  status: 'watching' | 'near_pivot' | 'triggered' | 'expired' | 'bought'
  note: string | null
  pattern?: Pattern
}

// === Signal Types ===

export interface Signal {
  id: number
  symbol: string
  name?: string
  signal_time: string
  signal_type: 'BUY' | 'SELL'
  direction: 'ENTER' | 'EXIT' | 'ADD' | 'REDUCE'
  price: number
  volume_confirmed: boolean
  market_confirmed: boolean
  risk_confirmed: boolean
  reason: string
  status: 'pending' | 'executed' | 'cancelled' | 'expired'
}

// === Position Types ===

export interface Position {
  id: number
  symbol: string
  quantity: number
  average_cost: number
  current_price?: number
  current_stop: number | null
  initial_stop: number | null
  highest_price: number | null
  pnl?: number
  pnl_pct?: number
  status: 'open' | 'closed'
  opened_at: string | null
  closed_at: string | null
}

// === Order Types ===

export interface Order {
  id: number
  symbol: string
  side: 'BUY' | 'SELL'
  order_type: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT'
  quantity: number
  limit_price: number | null
  stop_price: number | null
  status: 'pending' | 'submitted' | 'filled' | 'cancelled' | 'rejected'
  created_at: string
}

// === Trade Types ===

export interface Trade {
  id: number
  symbol: string
  side: string
  quantity: number
  price: number
  fee: number
  trade_time: string
  note: string | null
}

// === Backtest Types ===

export interface BacktestConfig {
  market: string
  start_date: string
  end_date: string
  initial_capital: number
  commission_pct: number
  slippage_pct: number
  symbols?: string[]
}

export interface BacktestResult {
  id: number
  config: BacktestConfig
  metrics: BacktestMetrics
  equity_curve: Array<{ date: string; value: number }>
  trades: Trade[]
  created_at: string
}

export interface BacktestMetrics {
  total_return: number
  cagr: number
  sharpe: number
  max_drawdown: number
  win_rate: number
  total_trades: number
  profit_factor: number
  avg_win: number
  avg_loss: number
  avg_holding_days: number
}

// === Dashboard Types ===

export interface DashboardData {
  market_phase: 'bull' | 'neutral' | 'bear'
  total_stocks_scanned: number
  stage2_passed: number
  rs_passed: number
  fundamental_passed: number
  patterns_found: number
  near_pivot: number
  today_buy_signals: number
  today_sell_signals: number
  account_equity: number
  total_position_pct: number
}

// === AI Report Types ===

export interface AIReport {
  date: string
  market_summary: string
  top_ideas: string[]
  risk_warnings: string[]
  focus_today: string[]
}
