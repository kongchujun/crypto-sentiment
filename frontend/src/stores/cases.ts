import { defineStore } from 'pinia'
import { ref } from 'vue'

import * as casesApi from '@/api/cases'
import * as cryptosApi from '@/api/cryptos'
import type { Case, CryptoMeta } from '@/types'

export const useCasesStore = defineStore('cases', () => {
  const cases = ref<Case[]>([])
  const cryptos = ref<CryptoMeta[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function loadCryptos() {
    if (cryptos.value.length > 0) return
    cryptos.value = await cryptosApi.listCryptos()
  }

  async function loadCases() {
    loading.value = true
    error.value = null
    try {
      cases.value = await casesApi.listCases()
    } catch (err) {
      error.value = (err as Error).message
    } finally {
      loading.value = false
    }
  }

  async function addCase(symbol: string): Promise<Case | null> {
    error.value = null
    try {
      const created = await casesApi.createCase(symbol)
      cases.value = [...cases.value, created]
      return created
    } catch (err) {
      error.value = (err as Error).message
      return null
    }
  }

  async function removeCase(id: number) {
    error.value = null
    try {
      await casesApi.deleteCase(id)
      cases.value = cases.value.filter((c) => c.id !== id)
    } catch (err) {
      error.value = (err as Error).message
    }
  }

  function cryptoNameFor(symbol: string): string {
    return cryptos.value.find((c) => c.symbol === symbol)?.name ?? symbol
  }

  return {
    cases,
    cryptos,
    loading,
    error,
    loadCryptos,
    loadCases,
    addCase,
    removeCase,
    cryptoNameFor,
  }
})
