<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import PostDetailDrawer from '@/components/PostDetailDrawer.vue'
import PostList from '@/components/PostList.vue'
import PriceChart from '@/components/PriceChart.vue'
import { fetchKlines, fetchTopPosts } from '@/api/cryptos'
import { listPredictionModels, predictPrice } from '@/api/prediction'
import { useCasesStore } from '@/stores/cases'
import type { Case, KlinePoint, PricePrediction, XPost } from '@/types'

const props = defineProps<{ caseData: Case }>()
const emit = defineEmits<{ remove: [] }>()

const store = useCasesStore()

const klines = ref<KlinePoint[]>([])
const posts = ref<XPost[]>([])
const klinesLoading = ref(false)
const postsLoading = ref(false)
const klinesError = ref<string | null>(null)
const hasFetchedPosts = ref(false)
const highlightedPostId = ref<string | null>(null)
const drawerVisible = ref(false)

const prediction = ref<PricePrediction | null>(null)
const predictLoading = ref(false)
const modelOptions = ref<{ id: string; label: string }[]>([])
const selectedModel = ref('')

const displayName = computed(() => store.cryptoNameFor(props.caseData.symbol))

const selectedPost = computed(
  () => posts.value.find((p) => p.id === highlightedPostId.value) ?? null,
)

const canPredict = computed(
  () => hasFetchedPosts.value && posts.value.length > 0 && klines.value.length > 0,
)

const predictionAlertType = computed(() => {
  if (!prediction.value) return 'info'
  const map = { bullish: 'success', bearish: 'error', neutral: 'info' } as const
  return map[prediction.value.direction]
})

const lastClose = computed(() => {
  if (klines.value.length === 0) return null
  return klines.value[klines.value.length - 1].close
})

const changePct = computed(() => {
  if (klines.value.length < 2) return null
  const first = klines.value[0].close
  const last = klines.value[klines.value.length - 1].close
  if (first === 0) return null
  return ((last - first) / first) * 100
})

async function loadModels() {
  try {
    const res = await listPredictionModels()
    modelOptions.value = res.models
    selectedModel.value = res.default_model
  } catch {
    modelOptions.value = []
  }
}

async function loadKlines() {
  klinesLoading.value = true
  klinesError.value = null
  try {
    klines.value = await fetchKlines(props.caseData.symbol, '15m', 24)
  } catch (err) {
    klinesError.value = (err as Error).message
    ElMessage.error(`Failed to load chart: ${klinesError.value}`)
  } finally {
    klinesLoading.value = false
  }
}

async function loadPosts() {
  postsLoading.value = true
  try {
    posts.value = await fetchTopPosts(props.caseData.symbol, 5)
    hasFetchedPosts.value = true
    prediction.value = null
  } catch (err) {
    ElMessage.error(`Failed to load posts: ${(err as Error).message}`)
  } finally {
    postsLoading.value = false
  }
}

async function runPredict() {
  if (!canPredict.value) {
    ElMessage.warning('Fetch X posts first, then run Predict.')
    return
  }
  predictLoading.value = true
  try {
    prediction.value = await predictPrice(props.caseData.symbol, {
      model: selectedModel.value || undefined,
      posts: posts.value,
      klines: klines.value,
    })
    const p = prediction.value
    const pct = Math.round(p.confidence * 100)
    ElMessage.success(`${p.direction} · ${pct}% confidence (${p.model})`)
  } catch (err) {
    ElMessage.error(`Prediction failed: ${(err as Error).message}`)
  } finally {
    predictLoading.value = false
  }
}

function onSelectPost(postId: string) {
  highlightedPostId.value = postId
  drawerVisible.value = true
}

onMounted(() => {
  loadKlines()
  loadModels()
})
</script>

<template>
  <el-card class="panel" shadow="hover">
    <template #header>
      <div class="panel__header">
        <div class="panel__title">
          <span class="panel__symbol">{{ displayName }}</span>
          <span class="panel__pair">{{ caseData.symbol }}</span>
          <span v-if="lastClose !== null" class="panel__price">
            ${{ lastClose.toLocaleString(undefined, { maximumFractionDigits: 4 }) }}
          </span>
          <span
            v-if="changePct !== null"
            class="panel__change"
            :class="{ 'is-up': changePct >= 0, 'is-down': changePct < 0 }"
          >
            {{ changePct >= 0 ? '+' : '' }}{{ changePct.toFixed(2) }}% (24h)
          </span>
        </div>
        <div class="panel__actions">
          <el-select
            v-model="selectedModel"
            placeholder="Model"
            size="default"
            class="panel__model-select"
            :disabled="modelOptions.length === 0"
          >
            <el-option
              v-for="m in modelOptions"
              :key="m.id"
              :label="m.label"
              :value="m.id"
            />
          </el-select>
          <el-button
            type="success"
            plain
            :loading="predictLoading"
            :disabled="!canPredict"
            @click="runPredict"
          >
            Predict
          </el-button>
          <el-button
            type="primary"
            plain
            :loading="postsLoading"
            @click="loadPosts"
          >
            {{ hasFetchedPosts ? 'Refresh X posts' : 'Fetch X posts' }}
          </el-button>
          <el-button :loading="klinesLoading" @click="loadKlines">Refresh chart</el-button>
          <el-popconfirm
            title="Remove this case?"
            confirm-button-text="Remove"
            @confirm="emit('remove')"
          >
            <template #reference>
              <el-button type="danger" plain>Remove</el-button>
            </template>
          </el-popconfirm>
        </div>
      </div>
    </template>

    <div class="panel__body">
      <div class="panel__chart">
        <el-alert
          v-if="prediction"
          class="panel__prediction-alert"
          :type="predictionAlertType"
          :closable="false"
          show-icon
        >
          <template #title>
            AI prediction (not financial advice) —
            {{ prediction.direction }}
            · {{ Math.round(prediction.confidence * 100) }}% · {{ prediction.horizon_hours }}h
          </template>
          {{ prediction.summary }}
        </el-alert>
        <el-skeleton v-if="klinesLoading && klines.length === 0" :rows="6" animated />
        <el-alert
          v-else-if="klinesError"
          type="error"
          :title="klinesError"
          show-icon
          :closable="false"
        />
        <PriceChart
          v-else
          :klines="klines"
          :posts="posts"
          :prediction="prediction"
          :highlighted-post-id="highlightedPostId"
          :symbol="caseData.symbol"
          @select-post="onSelectPost"
        />
      </div>
      <div class="panel__posts">
        <PostList
          :posts="posts"
          :highlighted-post-id="highlightedPostId"
          :loading="postsLoading"
          :has-fetched="hasFetchedPosts"
          @select-post="onSelectPost"
        />
      </div>
    </div>

    <PostDetailDrawer v-model="drawerVisible" :post="selectedPost" />
  </el-card>
</template>

<style scoped>
.panel {
  width: 100%;
}

.panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.panel__title {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.panel__symbol {
  font-size: 18px;
  font-weight: 600;
}

.panel__pair {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  letter-spacing: 0.5px;
}

.panel__price {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.panel__change {
  font-size: 13px;
  font-weight: 500;
}

.panel__change.is-up {
  color: var(--el-color-success);
}

.panel__change.is-down {
  color: var(--el-color-danger);
}

.panel__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.panel__model-select {
  width: 160px;
}

.panel__prediction-alert {
  margin-bottom: 12px;
}

.panel__body {
  display: grid;
  grid-template-columns: minmax(0, 7fr) minmax(280px, 3fr);
  gap: 16px;
}

.panel__chart {
  min-height: 360px;
}

.panel__posts {
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  padding: 12px;
  min-height: 360px;
}

@media (max-width: 900px) {
  .panel__body {
    grid-template-columns: 1fr;
  }
}
</style>
