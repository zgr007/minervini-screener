import { useQuery } from '@tanstack/react-query'
import { getPositions } from '../services/api'

export function usePositions() {
  return useQuery({
    queryKey: ['positions'],
    queryFn: () => getPositions().then(r => r.data.data),
    refetchInterval: 15000,
  })
}
