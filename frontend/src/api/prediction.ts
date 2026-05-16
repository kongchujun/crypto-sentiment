import { apiClient } from './client'
import type {
  KlinePoint,
  ModelsResponse,
  PricePrediction,
  XPost,
} from '@/types'

export async function listPredictionModels(): Promise<ModelsResponse> {
  const { data } = await apiClient.get<ModelsResponse>('/prediction/models')
  return data
}

export async function predictPrice(
  symbol: string,
  body: {
    model?: string
    posts: XPost[]
    klines: KlinePoint[]
  },
): Promise<PricePrediction> {
  const { data } = await apiClient.post<PricePrediction>(
    `/cryptos/${symbol}/predict`,
    body,
    { timeout: 90_000 },
  )
  return data
}
