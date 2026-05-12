import { apiClient } from './client'
import type { Case } from '@/types'

export async function listCases(): Promise<Case[]> {
  const { data } = await apiClient.get<Case[]>('/cases')
  return data
}

export async function createCase(symbol: string): Promise<Case> {
  const { data } = await apiClient.post<Case>('/cases', { symbol })
  return data
}

export async function deleteCase(id: number): Promise<void> {
  await apiClient.delete(`/cases/${id}`)
}
