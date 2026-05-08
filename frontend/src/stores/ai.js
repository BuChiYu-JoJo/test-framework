import { defineStore } from 'pinia'
import { ref } from 'vue'
import { locatorRepairApi } from '../api'

export const useAiStore = defineStore('ai', () => {
  const pendingRepairs = ref(0)
  const draftCount = ref(0)

  async function refreshPendingRepairs(projectId) {
    if (!projectId) { pendingRepairs.value = 0; return }
    try {
      const r = await locatorRepairApi.pendingCount(projectId)
      pendingRepairs.value = r?.data?.count ?? r?.count ?? 0
    } catch {
      pendingRepairs.value = 0
    }
  }

  function setDraftCount(count) {
    draftCount.value = count
  }

  return { pendingRepairs, draftCount, refreshPendingRepairs, setDraftCount }
})
