import axios from 'axios'
import type {
  ApiResponse,
  DashboardData,
  ScreenResult,
  WatchlistItem,
  Signal,
  Position,
  Order,
  Trade,
  BacktestConfig,
  BacktestResult,
  Pattern,
  Stock,
  StockDetailData,
  StockPriceData,
  AIReport,
} from './types'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error?.message || error.message || 'Unknown error'
    console.error('API Error:', message)
    return Promise.reject(error)
  }
)

// === Health ===

export const healthCheck = () => api.get('/health')

// === Data ===

export const updateData = (market: string) =>
  api.post<ApiResponse<{ task_id: string; market: string; status: string }>>('/api/data/update', { market })

export const getDataUpdateStatus = (taskId: string) =>
  api.get<ApiResponse<{ status: string; started_at?: string; completed_at?: string; error?: string }>>(`/api/data/update/${taskId}`)

export const getDataStatus = () =>
  api.get<ApiResponse<{
    last_update: Record<string, string | null>
    has_data: Record<string, boolean>
    stock_counts: Record<string, number>
  }>>('/api/data/status')

// === Screen ===

export const runScreen = (market: string) =>
  api.post<ApiResponse<{ run_id: string; status: string }>>('/api/screen/run', { market })

export const getScreenResults = () =>
  api.get<ApiResponse<ScreenResult[]>>('/api/screen/results')

// === Watchlist ===

export const getWatchlist = () =>
  api.get<ApiResponse<WatchlistItem[]>>('/api/watchlist')

export const addToWatchlist = (symbol: string, note?: string) =>
  api.post<ApiResponse<WatchlistItem>>('/api/watchlist', { symbol, note })

export const updateWatchlistItem = (id: number, data: Partial<WatchlistItem>) =>
  api.patch<ApiResponse<WatchlistItem>>(`/api/watchlist/${id}`, data)

export const removeFromWatchlist = (id: number) =>
  api.delete(`/api/watchlist/${id}`)

// === Stocks ===

export const getStockDetail = (symbol: string) =>
  api.get<ApiResponse<StockDetailData>>(`/api/stocks/${symbol}`)

export const getStockPrice = (symbol: string, days = 200) =>
  api.get<StockPriceData>(`/api/stock/${symbol}/price?days=${days}`)

export const getStockPatterns = (symbol: string) =>
  api.get<ApiResponse<Pattern[]>>(`/api/stocks/${symbol}/patterns`)

// === Signals ===

export const checkSignals = (symbols?: string[]) =>
  api.post<ApiResponse<Signal[]>>('/api/signals/check', { symbols })

export const getTodaySignals = () =>
  api.get<ApiResponse<Signal[]>>('/api/signals/today')

// === Orders ===

export const previewOrder = (symbol: string, side: string, quantity?: number) =>
  api.post<ApiResponse<Order>>('/api/orders/preview', { symbol, side, quantity })

export const simulateOrder = (order: Partial<Order>) =>
  api.post<ApiResponse<Order>>('/api/orders/simulate', order)

export const confirmOrder = (orderId: number) =>
  api.post<ApiResponse<Order>>('/api/orders/confirm', { order_id: orderId })

// === Positions ===

export const getPositions = () =>
  api.get<ApiResponse<Position[]>>('/api/positions')

// === Backtest ===

export const runBacktest = (config: BacktestConfig) =>
  api.post<ApiResponse<BacktestResult>>('/api/backtests/run', config)

export const getBacktests = () =>
  api.get<ApiResponse<BacktestResult[]>>('/api/backtests')

// === Reports ===

export const getDailyReport = () =>
  api.get<ApiResponse<AIReport>>('/api/reports/daily')

// === Notify ===

export const testNotify = (channel: string) =>
  api.post<ApiResponse<{ sent: boolean }>>('/api/notify/test', { channel })

// === Risk ===

export const getPortfolioRisk = () =>
  api.get<ApiResponse<{
    total_exposure: number
    market_phase: string
    var: number
    concentration: Record<string, number>
  }>>('/api/risk/portfolio')

export const getMarketPhase = () =>
  api.get<ApiResponse<{ phase: string; reason: string }>>('/api/risk/market')

// === Dashboard ===

export const getDashboard = () =>
  api.get<ApiResponse<DashboardData>>('/api/dashboard')

// === Stock Browser (Search & Add) ===

export interface StockSearchResult {
  code: string
  name: string
  market: string
  sector?: string
}

export interface TrackedStock {
  symbol: string
  name: string
  market: string
}

export const searchStocks = (q: string, market: string = 'CN', limit: number = 20, localOnly: boolean = false) =>
  api.get<ApiResponse<StockSearchResult[]>>('/api/stock-browser/search', { params: { q, market, limit, local_only: localOnly } })

export const addTrackedStock = (symbol: string, market: string, name?: string) =>
  api.post<ApiResponse<{ symbol: string; market: string; status: string }>>('/api/stock-browser/add', { symbol, market, name })

export const removeTrackedStock = (market: string, symbol: string) =>
  api.delete(`/api/stock-browser/remove/${market}/${symbol}`)

export const getTrackedStocks = (market?: string) =>
  api.get<ApiResponse<TrackedStock[]>>('/api/stock-browser/tracked', { params: { market } })

export default api
