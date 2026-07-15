import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getBacktests, runBacktest } from '../services/api'
import type { BacktestConfig } from '../services/types'

export function useBacktests() {
  return useQuery({
    queryKey: ['backtests'],
    queryFn: () => getBacktests().then(r => r.data.data),
  })
}

export function useRunBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (config: BacktestConfig) => runBacktest(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })
}
