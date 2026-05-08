import { defineStore } from 'pinia'
import { ref } from 'vue'
import { casesApi } from '../api'

export const useCasesStore = defineStore('cases', () => {
  const cases = ref([])
  const loading = ref(false)
  const filters = ref({ project_id: null, module: '', priority: '' })

  async function fetchCases(params = {}) {
    loading.value = true
    try {
      const queryParams = { ...filters.value, ...params }
      // 去掉空值
      Object.keys(queryParams).forEach((k) => {
        if (queryParams[k] === '' || queryParams[k] === null) delete queryParams[k]
      })
      cases.value = await casesApi.list(queryParams)
    } finally {
      loading.value = false
    }
  }

  async function createCase(data) {
    await casesApi.create(data)
    await fetchCases()
  }

  async function updateCase(id, data) {
    await casesApi.update(id, data)
    await fetchCases()
  }

  async function deleteCase(id) {
    await casesApi.delete(id)
    await fetchCases()
  }

  async function duplicateCase(id) {
    await casesApi.duplicate(id)
    await fetchCases()
  }

  return { cases, loading, filters, fetchCases, createCase, updateCase, deleteCase, duplicateCase }
})
