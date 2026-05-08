import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/index'

export const useCrawlerStore = defineStore('crawler', () => {
  const configs = ref([])
  const inspections = ref([])
  const stats = ref(null)
  const loading = ref(false)

  async function fetchConfigs(params = {}) {
    loading.value = true
    try {
      const res = await api.get('/crawler/configs', { params })
      configs.value = res
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    const res = await api.get('/crawler/stats')
    stats.value = res
  }

  async function createConfig(data) {
    const res = await api.post('/crawler/configs', data)
    await fetchConfigs()
    return res
  }

  async function updateConfig(id, data) {
    await api.put(`/crawler/configs/${id}`, data)
    await fetchConfigs()
  }

  async function deleteConfig(id) {
    await api.delete(`/crawler/configs/${id}`)
    configs.value = configs.value.filter(c => c.id !== id)
  }

  async function runNow(id) {
    return await api.post(`/crawler/configs/${id}/run`)
  }

  async function fetchInspections(crawlerId) {
    const res = await api.get('/crawler/inspections', { params: crawlerId ? { crawler_id: crawlerId } : {} })
    inspections.value = res
  }

  return { configs, inspections, stats, loading, fetchConfigs, fetchStats, createConfig, updateConfig, deleteConfig, runNow, fetchInspections }
})
