<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, ScatterChart } from 'echarts/charts'
import {
  DataZoomComponent,
  GridComponent,
  MarkPointComponent,
  TitleComponent,
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

import type { KlinePoint, PricePrediction, XPost } from '@/types'
import { computeScatterPoints } from './scatterPoints'

echarts.use([
  LineChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  TitleComponent,
  DataZoomComponent,
  MarkPointComponent,
  CanvasRenderer,
])

const props = defineProps<{
  klines: KlinePoint[]
  posts: XPost[]
  prediction: PricePrediction | null
  highlightedPostId: string | null
  symbol: string
}>()

const emit = defineEmits<{ 'select-post': [postId: string] }>()

const containerRef = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)

const lineSeriesData = computed(() =>
  props.klines.map((k) => [k.open_time, k.close]),
)

const scatterPoints = computed(() => computeScatterPoints(props.klines, props.posts))

const forecastColor = computed(() => {
  if (!props.prediction) return '#909399'
  const map = { bullish: '#67c23a', bearish: '#f56c6c', neutral: '#909399' } as const
  return map[props.prediction.direction]
})

const forecastSeriesData = computed(() => {
  if (!props.prediction || props.klines.length === 0) return []
  const last = props.klines[props.klines.length - 1]
  const anchor: [number, number] = [last.open_time, last.close]
  const points: [number, number][] = props.prediction.forecast_points.map((p) => [
    p.open_time,
    p.price,
  ])
  return [anchor, ...points]
})

function buildOption(): echarts.EChartsCoreOption {
  const postById = new Map(props.posts.map((p) => [p.id, p]))
  const highlightedId = props.highlightedPostId

  const series: Record<string, unknown>[] = [
    {
      name: 'Price',
      type: 'line',
      showSymbol: false,
      smooth: true,
      sampling: 'lttb',
      data: lineSeriesData.value,
      lineStyle: { width: 2, color: '#409eff' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(64,158,255,0.25)' },
            { offset: 1, color: 'rgba(64,158,255,0)' },
          ],
        },
      },
    },
    {
      name: 'Posts',
      type: 'scatter',
      symbol: 'circle',
      symbolSize: (_value: unknown, params: any) =>
        params?.data?.postId === highlightedId ? 18 : 12,
      itemStyle: {
        color: (params: any) =>
          params?.data?.postId === highlightedId ? '#f56c6c' : '#e6a23c',
        borderColor: '#fff',
        borderWidth: 2,
        shadowBlur: 6,
        shadowColor: 'rgba(230,162,60,0.4)',
      },
      emphasis: { scale: 1.2 },
      z: 5,
      data: scatterPoints.value,
    },
  ]

  if (forecastSeriesData.value.length > 0) {
    series.push({
      name: 'Forecast',
      type: 'line',
      showSymbol: true,
      symbolSize: 6,
      smooth: false,
      data: forecastSeriesData.value,
      lineStyle: {
        type: 'dashed',
        width: 2,
        color: forecastColor.value,
      },
      itemStyle: { color: forecastColor.value },
      z: 4,
    })
  }

  return {
    grid: { left: 56, right: 24, top: 24, bottom: 48 },
    legend: props.prediction
      ? { data: ['Price', 'Posts', 'Forecast'], top: 0, right: 8 }
      : undefined,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        if (!Array.isArray(params)) params = [params]
        const line: string[] = []
        for (const p of params) {
          const time = new Date(p.value[0]).toLocaleString()
          if (p.seriesName === 'Price') {
            line.push(`<b>${time}</b><br/>Price: ${Number(p.value[1]).toFixed(4)}`)
          } else if (p.seriesName === 'Forecast') {
            line.push(
              `<b>${time}</b><br/>Predicted: ${Number(p.value[1]).toFixed(4)}`,
            )
          } else if (p.seriesName === 'Posts' && p.data?.postId) {
            const post = postById.get(p.data.postId)
            if (post) {
              const preview =
                post.content.length > 80 ? `${post.content.slice(0, 80)}…` : post.content
              line.push(`<b>${post.author}</b><br/>${preview}`)
            }
          }
        }
        return line.join('<hr style="margin:4px 0;border:none;border-top:1px solid #eee" />')
      },
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#909399' } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { lineStyle: { color: '#909399' } },
      splitLine: { lineStyle: { color: '#ebeef5' } },
    },
    dataZoom: [
      { type: 'inside', throttle: 50 },
      { type: 'slider', height: 18, bottom: 12 },
    ],
    series,
  }
}

function applyOption() {
  if (!chart.value) return
  chart.value.setOption(buildOption(), { notMerge: true })
}

function handleResize() {
  chart.value?.resize()
}

onMounted(() => {
  if (!containerRef.value) return
  chart.value = echarts.init(containerRef.value)
  chart.value.on('click', (params: any) => {
    if (params?.seriesName === 'Posts' && params?.data?.postId) {
      emit('select-post', params.data.postId as string)
    }
  })
  applyOption()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart.value?.dispose()
  chart.value = null
})

watch(
  () => [
    props.klines,
    props.posts,
    props.prediction,
    props.highlightedPostId,
    props.symbol,
  ],
  () => applyOption(),
  { deep: true },
)
</script>

<template>
  <div ref="containerRef" class="price-chart" />
</template>

<style scoped>
.price-chart {
  width: 100%;
  height: 360px;
}
</style>
