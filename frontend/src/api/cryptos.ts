import { apiClient } from './client'
import type { CryptoMeta, KlinePoint, XPost } from '@/types'

export async function listCryptos(): Promise<CryptoMeta[]> {
  const { data } = await apiClient.get<CryptoMeta[]>('/cryptos')
  return data
}

export async function fetchKlines(
  symbol: string,
  interval = '15m',
  hours = 24,
): Promise<KlinePoint[]> {
  const { data } = await apiClient.get<KlinePoint[]>(`/cryptos/${symbol}/klines`, {
    params: { interval, hours },
  })
  return data
}

export async function fetchTopPosts(symbol: string, limit = 5): Promise<XPost[]> {
  const { data } = await apiClient.get<XPost[]>(`/cryptos/${symbol}/posts`, {
    params: { limit },
  })
  return data
}
