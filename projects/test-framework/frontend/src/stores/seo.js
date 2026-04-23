import { defineStore } from 'pinia'
import { ref } from 'vue'
import { seoApi } from '../api/seo'

export const useSeoStore = defineStore('seo', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const issues = ref([])
  const loading = ref(false)

  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      tasks.value = await seoApi.list(params)
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(taskId) {
    loading.value = true
    try {
      currentTask.value = await seoApi.get(taskId)
      issues.value = await seoApi.getIssues(taskId)
    } finally {
      loading.value = false
    }
  }

  async function createTask(data) {
    const result = await seoApi.create(data)
    await fetchTasks()
    return result
  }

  async function deleteTask(taskId) {
    await seoApi.delete(taskId)
    tasks.value = tasks.value.filter(t => t.id !== taskId)
    if (currentTask.value && currentTask.value.id === taskId) {
      currentTask.value = null
    }
  }

  async function runTask(taskId) {
    return await seoApi.run(taskId)
  }

  async function fetchReport(taskId) {
    return await seoApi.getReport(taskId)
  }

  return {
    tasks,
    currentTask,
    issues,
    loading,
    fetchTasks,
    fetchTask,
    createTask,
    deleteTask,
    runTask,
    fetchReport,
  }
})