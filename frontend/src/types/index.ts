export interface CryptoMeta {
  symbol: string
  name: string
  base_asset: string
}

export interface KlinePoint {
  open_time: number
  close: number
}

export interface XPost {
  id: string
  author: string
  content: string
  created_at: number
  likes: number
  retweets: number
  url: string | null
}

export interface Case {
  id: number
  symbol: string
  created_at: string
}

export interface ForecastPoint {
  open_time: number
  price: number
}

export type PredictionDirection = 'bullish' | 'bearish' | 'neutral'

export interface PricePrediction {
  direction: PredictionDirection
  confidence: number
  horizon_hours: number
  summary: string
  forecast_points: ForecastPoint[]
  model: string
}

export interface ModelOption {
  id: string
  label: string
}

export interface ModelsResponse {
  models: ModelOption[]
  default_model: string
}
