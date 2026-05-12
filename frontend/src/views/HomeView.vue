<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AddCaseDialog from '@/components/AddCaseDialog.vue'
import CryptoPanel from '@/components/CryptoPanel.vue'
import { useCasesStore } from '@/stores/cases'

const store = useCasesStore()
const dialogVisible = ref(false)

onMounted(async () => {
  await Promise.all([store.loadCryptos(), store.loadCases()])
})

function openDialog() {
  dialogVisible.value = true
}
</script>

<template>
  <div class="home">
    <header class="home__header">
      <div class="home__title">
        <h1>Crypto Sentiment</h1>
        <p>Crypto prices + X (Twitter) chatter, side by side.</p>
      </div>
      <el-button type="primary" size="large" @click="openDialog">
        <el-icon style="margin-right: 4px"><svg viewBox="0 0 1024 1024" width="1em" height="1em"><path fill="currentColor" d="M480 480V128h64v352h352v64H544v352h-64V544H128v-64z"/></svg></el-icon>
        Add Case
      </el-button>
    </header>

    <el-empty
      v-if="!store.loading && store.cases.length === 0"
      description="No cases yet. Click 'Add Case' to track a coin."
    />

    <div v-else class="home__panels">
      <CryptoPanel
        v-for="kase in store.cases"
        :key="kase.id"
        :case-data="kase"
        @remove="store.removeCase(kase.id)"
      />
    </div>

    <AddCaseDialog v-model="dialogVisible" />
  </div>
</template>

<style scoped>
.home {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.home__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 24px;
}

.home__title h1 {
  margin: 0 0 4px;
  font-size: 24px;
}

.home__title p {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.home__panels {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
</style>
