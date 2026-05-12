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
