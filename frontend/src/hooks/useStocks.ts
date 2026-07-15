import { useQuery } from '@tanstack/react-query'
import { getStockDetail, getStockPatterns, getScreenResults } from '../services/api'

export function useStockDetail(symbol: string) {
  return useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => getStockDetail(symbol).then(r => r.data.data),
    enabled: !!symbol,
  })
}

export function useStockPatterns(symbol: string) {
  return useQuery({
    queryKey: ['stock-patterns', symbol],
    queryFn: () => getStockPatterns(symbol).then(r => r.data.data),
    enabled: !!symbol,
  })
}

export function useScreenResults() {
  return useQuery({
    queryKey: ['screen-results'],
    queryFn: () => getScreenResults().then(r => r.data.data),
    refetchInterval: 60000,
  })
}
