import { defineStore } from 'pinia'
import { ref } from 'vue'
import { performanceApi } from '../api'

export const usePerformanceStore = defineStore('performance', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const loading = ref(false)

  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      tasks.value = await performanceApi.list(params)
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(taskId) {
    loading.value = true
    try {
      currentTask.value = await performanceApi.get(taskId)
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    const result = await performanceApi.create(data)
    await fetchTasks()
    return result
  }

  async function deleteTask(taskId) {
    await performanceApi.delete(taskId)
    tasks.value = tasks.value.filter(t => t.id !== taskId)
    if (currentTask.value && currentTask.value.id === taskId) {
      currentTask.value = null
    }
  }

  return {
    tasks,
    currentTask,
    loading,
    fetchTasks,
    fetchTask,
    createTask,
    deleteTask,
  }
})