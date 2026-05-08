import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/index'

export const useProxyStore = defineStore('proxy', () => {
  const proxies = ref([])
  const groups = ref([])
  const stats = ref(null)
  const loading = ref(false)

  async function fetchProxies(params = {}) {
    loading.value = true
    try {
      const res = await api.get('/proxy/list', { params })
      proxies.value = res
    } finally {
      loading.value = false
    }
  }

  async function fetchGroups() {
    const res = await api.get('/proxy/groups')
    groups.value = res
  }

  async function fetchStats() {
    const res = await api.get('/proxy/stats')
    stats.value = res
  }

  async function addProxy(data) {
    await api.post('/proxy/add', data)
    await fetchProxies()
    await fetchStats()
  }

  async function batchImport(items) {
    return await api.post('/proxy/batch', { proxies: items })
  }

  async function deleteProxy(id) {
    await api.delete(`/proxy/${id}`)
    proxies.value = proxies.value.filter(p => p.id !== id)
  }

  async function testProxy(id) {
    return await api.post(`/proxy/${id}/test`)
  }

  async function refreshAll() {
    return await api.post('/proxy/refresh')
  }

  return { proxies, groups, stats, loading, fetchProxies, fetchGroups, fetchStats, addProxy, batchImport, deleteProxy, testProxy, refreshAll }
})
