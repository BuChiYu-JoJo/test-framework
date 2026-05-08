import { defineStore } from 'pinia'
import { ref } from 'vue'

const BASE_URL = () => {
  const isDev = window.location.hostname === 'localhost' && window.location.port === '3000'
  return isDev ? 'http://localhost:8000' : ''
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref([])
  const currentTask = ref(null)
  const currentReport = ref(null)
  const loading = ref(false)
  let sseSource = null

  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      const qs = new URLSearchParams(params).toString()
      const res = await fetch(`${BASE_URL()}/api/v1/tasks?${qs}`)
      const json = await res.json()
      tasks.value = json.data?.items || json.items || json.data || []
    } finally {
      loading.value = false
    }
  }

  async function fetchTask(taskId) {
    const res = await fetch(`${BASE_URL()}/api/v1/tasks/${taskId}`)
    const json = await res.json()
    currentTask.value = json.data || json
  }

  async function fetchTaskReport(taskId) {
    const res = await fetch(`${BASE_URL()}/api/v1/tasks/${taskId}/report`)
    const json = await res.json()
    currentReport.value = json.data || json
    return currentReport.value
  }

  function subscribeSSE(taskId, { onStep, onDone, onError } = {}) {
    unsubscribeSSE()
    const url = `${BASE_URL()}/api/v1/tasks/${taskId}/stream`
    const es = new EventSource(url)

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'done') {
          if (onDone) onDone(data)
          unsubscribeSSE()
        } else if (onStep) {
          onStep(data)
        }
      } catch {}
    }

    es.onerror = () => {
      if (onError) onError()
      unsubscribeSSE()
    }

    sseSource = es
  }

  function unsubscribeSSE() {
    if (sseSource) {
      sseSource.close()
      sseSource = null
    }
  }

  return {
    tasks,
    currentTask,
    currentReport,
    loading,
    fetchTasks,
    fetchTask,
    fetchTaskReport,
    subscribeSSE,
    unsubscribeSSE,
  }
})
