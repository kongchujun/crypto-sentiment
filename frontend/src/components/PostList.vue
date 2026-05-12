<script setup lang="ts">
import type { XPost } from '@/types'

defineProps<{
  posts: XPost[]
  highlightedPostId: string | null
  loading: boolean
  hasFetched: boolean
}>()

const emit = defineEmits<{ 'select-post': [postId: string] }>()

function formatRelative(ts: number): string {
  const diffMs = Date.now() - ts
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}

function truncate(text: string, limit = 90): string {
  return text.length > limit ? `${text.slice(0, limit)}…` : text
}
</script>

<template>
  <div class="post-list">
    <div class="post-list__header">
      <span>Top X posts</span>
      <span class="post-list__count" v-if="hasFetched && !loading">{{ posts.length }}</span>
    </div>

    <el-skeleton v-if="loading" :rows="4" animated style="padding: 12px" />

    <el-empty
      v-else-if="!hasFetched"
      description="Click 'Fetch X posts' to load chatter"
      :image-size="60"
    />

    <el-empty
      v-else-if="posts.length === 0"
      description="No posts found"
      :image-size="60"
    />

    <el-scrollbar v-else max-height="320px">
      <div
        v-for="post in posts"
        :key="post.id"
        class="post-card"
        :class="{ 'post-card--active': post.id === highlightedPostId }"
        @click="emit('select-post', post.id)"
      >
        <div class="post-card__meta">
          <strong>{{ post.author }}</strong>
          <span>{{ formatRelative(post.created_at) }}</span>
        </div>
        <p class="post-card__content">{{ truncate(post.content) }}</p>
        <div class="post-card__stats">
          <span>❤ {{ post.likes.toLocaleString() }}</span>
          <span>↻ {{ post.retweets.toLocaleString() }}</span>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<style scoped>
.post-list {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.post-list__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  border-bottom: 1px solid var(--el-border-color-lighter);
  margin-bottom: 8px;
}

.post-list__count {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-radius: 10px;
  padding: 0 8px;
  font-size: 11px;
}

.post-card {
  border-radius: 8px;
  padding: 10px 12px;
  margin: 4px 6px;
  cursor: pointer;
  transition: background 0.15s, border 0.15s;
  border: 1px solid transparent;
  background: var(--el-bg-color);
}

.post-card:hover {
  background: var(--el-color-primary-light-9);
}

.post-card--active {
  border-color: var(--el-color-danger);
  background: var(--el-color-danger-light-9);
}

.post-card__meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin-bottom: 4px;
}

.post-card__content {
  margin: 0 0 6px;
  font-size: 13px;
  line-height: 1.4;
  color: var(--el-text-color-primary);
}

.post-card__stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
