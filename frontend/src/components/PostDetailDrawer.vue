<script setup lang="ts">
import { computed } from 'vue'

import type { XPost } from '@/types'

const props = defineProps<{
  modelValue: boolean
  post: XPost | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

function formatAbsolute(ts: number): string {
  return new Date(ts).toLocaleString()
}
</script>

<template>
  <el-drawer
    v-model="visible"
    title="Post detail"
    direction="rtl"
    size="420px"
  >
    <div v-if="post" class="post-detail">
      <div class="post-detail__meta">
        <strong>{{ post.author }}</strong>
        <span>{{ formatAbsolute(post.created_at) }}</span>
      </div>
      <p class="post-detail__content">{{ post.content }}</p>
      <div class="post-detail__stats">
        <span>❤ {{ post.likes.toLocaleString() }} likes</span>
        <span>↻ {{ post.retweets.toLocaleString() }} reposts</span>
      </div>
      <el-link
        v-if="post.url"
        :href="post.url"
        target="_blank"
        type="primary"
        underline="never"
      >
        Open on X →
      </el-link>
    </div>
  </el-drawer>
</template>

<style scoped>
.post-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.post-detail__meta {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.post-detail__content {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
}

.post-detail__stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
