import { defineStore } from 'pinia'
import { ref } from 'vue'
import { executionsApi } from '../api'

export const useExecutionStore = defineStore('execution', () => {
  const executions = ref([])
  const currentExecution = ref(null)
  const currentSteps = ref([])
  const loading = ref(false)
  const debugLogs = ref([])
  let eventSource = null
  let debugEventSource = null

  async function fetchExecutions(params = {}) {
    loading.value = true
    try {
      executions.value = await executionsApi.list(params)
    } finally {
      loading.value = false
    }
  }

  async function fetchExecution(executionId) {
    loading.value = true
    try {
      currentExecution.value = await executionsApi.get(executionId)
      currentSteps.value = await executionsApi.getSteps(executionId)
    } finally {
      loading.value = false
    }
  }

  async function createExecution(data) {
    const result = await executionsApi.create(data)
    await fetchExecutions()
    return result
  }

  function addStep(step) {
    // addStep 处理所有步骤来源：DB历史 + SSE实时 + SSE重放
    // 去重：同 step_no 已存在则更新，不存在则追加
    const idx = currentSteps.value.findIndex(s => s.step_no === step.step_no)
    if (idx >= 0) {
      currentSteps.value[idx] = { ...step }
    } else {
      currentSteps.value.push({ ...step })
      currentSteps.value.sort((a, b) => a.step_no - b.step_no)
    }
  }

  function updateExecutionStatus(data) {
    if (currentExecution.value) {
      currentExecution.value.status = data.status
      currentExecution.value.result = data.result
      currentExecution.value.duration_ms = data.duration_ms
      currentExecution.value.error_msg = data.error_msg
    }
  }

  function startStreaming(executionId) {
    // 先停止旧连接（避免串台）
    stopStreaming()
    // 不清空 currentSteps：fetchExecution 已加载了 DB 中的历史 steps
    // SSE 重放会通过 addStep 追加（去重），实时步骤也会通过 addStep 追加

    const isDev = window.location.hostname === 'localhost' && window.location.port === '3000'
    const baseUrl = isDev ? 'http://localhost:8000' : ''
    const url = `${baseUrl}/api/v1/executions/${executionId}/stream`
    const es = new EventSource(url)

    es.onopen = () => {
      console.log('[SSE] Connected:', url)
    }

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'step') {
          addStep(data)
        } else if (data.type === 'done') {
          updateExecutionStatus(data)
          stopStreaming()
        }
      } catch (err) {
        console.error('[SSE] Parse error:', err)
      }
    }

    es.onerror = (err) => {
      console.error('[SSE] Error:', err)
    }

    eventSource = es
  }

  function stopStreaming() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function startDebugStreaming(executionId) {
    stopDebugStreaming()
    debugLogs.value = []

    const isDev = window.location.hostname === 'localhost' && window.location.port === '3000'
    const baseUrl = isDev ? 'http://localhost:8000' : ''
    const url = `${baseUrl}/api/v1/executions/${executionId}/debug-stream`
    const es = new EventSource(url)

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'done') {
          stopDebugStreaming()
        } else {
          debugLogs.value.push(data)
        }
      } catch (err) {
        console.error('[Debug SSE] Parse error:', err)
      }
    }

    es.onerror = (err) => {
      console.error('[Debug SSE] Error:', err)
      stopDebugStreaming()
    }

    debugEventSource = es
  }

  function stopDebugStreaming() {
    if (debugEventSource) {
      debugEventSource.close()
      debugEventSource = null
    }
  }

  return {
    executions,
    currentExecution,
    currentSteps,
    debugLogs,
    loading,
    fetchExecutions,
    fetchExecution,
    createExecution,
    addStep,
    updateExecutionStatus,
    startStreaming,
    stopStreaming,
    startDebugStreaming,
    stopDebugStreaming,
  }
})
