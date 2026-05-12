import type { KlinePoint, XPost } from '@/types'

const BUCKET_MS = 15 * 60 * 1000

export interface ScatterPoint {
  value: [number, number]
  postId: string
}

function findClosestClose(klines: KlinePoint[], t: number): number {
  if (klines.length === 0) return 0
  let lo = 0
  let hi = klines.length - 1
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (klines[mid].open_time < t) lo = mid + 1
    else hi = mid
  }
  const candidate = klines[lo]
  const prev = klines[Math.max(0, lo - 1)]
  return Math.abs(candidate.open_time - t) <= Math.abs(prev.open_time - t)
    ? candidate.close
    : prev.close
}

/**
 * Build scatter points for the chart, one per post.
 *
 * Posts in the same 15-minute bucket are offset vertically around the line's
 * closing price so they don't overlap visually. The vertical step is ~1% of
 * the visible price range.
 */
export function computeScatterPoints(
  klines: KlinePoint[],
  posts: XPost[],
): ScatterPoint[] {
  if (posts.length === 0 || klines.length === 0) return []

  const buckets = new Map<number, XPost[]>()
  for (const post of posts) {
    const bucketStart = Math.floor(post.created_at / BUCKET_MS) * BUCKET_MS
    const group = buckets.get(bucketStart)
    if (group) group.push(post)
    else buckets.set(bucketStart, [post])
  }

  const closes = klines.map((k) => k.close)
  const priceRange = Math.max(...closes) - Math.min(...closes)
  const delta = priceRange === 0 ? 1 : priceRange * 0.012

  const points: ScatterPoint[] = []
  for (const [, group] of buckets) {
    group.sort((a, b) => a.created_at - b.created_at)
    group.forEach((post, idx) => {
      const baseY = findClosestClose(klines, post.created_at)
      const offset = (idx - (group.length - 1) / 2) * delta
      points.push({
        value: [post.created_at, baseY + offset],
        postId: post.id,
      })
    })
  }
  return points
}
