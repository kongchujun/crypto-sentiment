<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { useCasesStore } from '@/stores/cases'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const store = useCasesStore()
const selected = ref<string>('')
const submitting = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const usedSymbols = computed(() => new Set(store.cases.map((c) => c.symbol)))

const options = computed(() =>
  store.cryptos.map((c) => ({
    value: c.symbol,
    label: `${c.name} (${c.base_asset})`,
    disabled: usedSymbols.value.has(c.symbol),
  })),
)

watch(visible, (open) => {
  if (open) {
    selected.value = ''
  }
})

async function handleConfirm() {
  if (!selected.value) {
    ElMessage.warning('Please select a cryptocurrency')
    return
  }
  submitting.value = true
  const created = await store.addCase(selected.value)
  submitting.value = false
  if (created) {
    ElMessage.success(`Added ${store.cryptoNameFor(created.symbol)} panel`)
    visible.value = false
  } else if (store.error) {
    ElMessage.error(store.error)
  }
}
</script>

<template>
  <el-dialog v-model="visible" title="Add Case" width="420px">
    <el-form label-position="top">
      <el-form-item label="Cryptocurrency">
        <el-select
          v-model="selected"
          placeholder="Choose a coin"
          style="width: 100%"
          filterable
        >
          <el-option
            v-for="option in options"
            :key="option.value"
            :value="option.value"
            :label="option.label"
            :disabled="option.disabled"
          />
        </el-select>
      </el-form-item>
      <p class="hint">
        Already-tracked coins are disabled. Each case shows a 24h price chart and the top
        X posts on demand.
      </p>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">Cancel</el-button>
      <el-button type="primary" :loading="submitting" @click="handleConfirm">
        Create panel
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.hint {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
