import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/Layout'
import Dashboard from './pages/Dashboard'
import ScreenResults from './pages/ScreenResults'
import Watchlist from './pages/Watchlist'
import StockDetail from './pages/StockDetail'
import Positions from './pages/Positions'
import Backtest from './pages/Backtest'
import TradeLogs from './pages/TradeLogs'
import Settings from './pages/Settings'

const App: React.FC = () => {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/screen" element={<ScreenResults />} />
        <Route path="/watchlist" element={<Watchlist />} />
        <Route path="/stock/:symbol" element={<StockDetail />} />
        <Route path="/positions" element={<Positions />} />
        <Route path="/backtest" element={<Backtest />} />
        <Route path="/trades" element={<TradeLogs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  )
}

export default App
