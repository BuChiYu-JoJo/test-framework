import axios from 'axios'
import { ElMessage } from 'element-plus'

const BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

// 响应拦截器
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const msg = error.response?.data?.detail || error.message || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

// ─── Projects ────────────────────────────────────────────────
export const projectsApi = {
  list: () => api.get('/projects'),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.put(`/projects/${id}`, data),
  delete: (id) => api.delete(`/projects/${id}`),
}

// ─── Cases ───────────────────────────────────────────────────
export const casesApi = {
  list: (params) => api.get('/cases', { params }),
  get: (id) => api.get(`/cases/${id}`),
  create: (data) => api.post('/cases', data),
  update: (id, data) => api.put(`/cases/${id}`, data),
  delete: (id) => api.delete(`/cases/${id}`),
  duplicate: (id) => api.post(`/cases/${id}/duplicate`),
  import: (projectId, formData) =>
    api.post(`/cases/import?project_id=${projectId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  downloadTemplate: () =>
    api.get('/cases/template/download', { responseType: 'blob' }),
}

// ─── Executions ───────────────────────────────────────────────
export const executionsApi = {
  list: (params) => api.get('/executions', { params }),
  get: (executionId) => api.get(`/executions/${executionId}`),
  create: (data) => api.post('/executions', data),
  getSteps: (executionId) => api.get(`/executions/${executionId}/steps`),
  stream: (executionId) => new EventSource(`/api/v1/executions/${executionId}/stream`),
}

// ─── Reports ──────────────────────────────────────────────────
export const reportsApi = {
  history: (params) => api.get('/reports/history', { params }),
  get: (executionId) => api.get(`/reports/${executionId}`),
}

// ─── Locators ─────────────────────────────────────────────────
export const locatorsApi = {
  list: (projectId, pageName) =>
    api.get('/locators', { params: { project_id: projectId, page_name: pageName } }),
  listPages: (projectId) => api.get(`/locators/pages/${projectId}`),
  create: (data) => api.post('/locators', data),
  update: (id, data) => api.put(`/locators/${id}`, data),
  delete: (id) => api.delete(`/locators/${id}`),
  export: (projectId) => api.get(`/locators/export/${projectId}`),
  import: (projectId, data) => api.post(`/locators/import/${projectId}`, data),
  initSample: (projectId) => api.get(`/locators/init-sample/${projectId}`),
}

// ─── Scheduler ─────────────────────────────────────────────────
export const schedulerApi = {
  list: (params) => api.get('/scheduler/jobs', { params }),
  get: (jobId) => api.get(`/scheduler/jobs/${jobId}`),
  create: (data) => api.post('/scheduler/jobs', data),
  update: (jobId, data) => api.put(`/scheduler/jobs/${jobId}`, data),
  delete: (jobId) => api.delete(`/scheduler/jobs/${jobId}`),
  run: (jobId) => api.post(`/scheduler/jobs/${jobId}/run`),
}

// ─── Settings ──────────────────────────────────────────────────
export const settingsApi = {
  getNotify: () => api.get('/settings/notify'),
  saveNotify: (data) => api.post('/settings/notify', data),
  testNotify: (data) => api.post('/settings/notify/test', data),
}

// ─── Performance ─────────────────────────────────────────────────
export const performanceApi = {
  list: (params) => api.get('/performance/tasks', { params }),
  get: (id) => api.get(`/performance/tasks/${id}`),
  create: (data) => api.post('/performance/tasks', data),
  delete: (id) => api.delete(`/performance/tasks/${id}`),
}

// ─── AI Tools ──────────────────────────────────────────────────
export const aiApi = {
  generateLocators: (data) => api.post('/ai/locators/generate', data, { timeout: 180000 }),
  generateLocatorsWithAuth: (data) => api.post('/ai/locators/generate-with-auth', data, { timeout: 300000 }),
  enhanceLocators: (data) => api.post('/ai/locators/enhance', data),
  listLoginCases: (projectId) => api.get('/ai/locators/login-cases', { params: { project_id: projectId } }),
  generateCase: (data) => api.post('/ai/cases/generate', data),
  selectRegression: (data) => api.post('/ai/regression/select', data),
}

// ─── API Test ──────────────────────────────────────────────────
export const apiTestApi = {
  listCases: (params) => api.get('/api-test/cases', { params }),
  getCase: (id) => api.get(`/api-test/cases/${id}`),
  createCase: (data) => api.post('/api-test/cases', data),
  updateCase: (id, data) => api.put(`/api-test/cases/${id}`, data),
  deleteCase: (id) => api.delete(`/api-test/cases/${id}`),
  runCase: (id, env = 'dev') => api.post(`/api-test/cases/${id}/run?env=${env}`),
  listTasks: (params) => api.get('/api-test/tasks', { params }),
  getTask: (id) => api.get(`/api-test/tasks/${id}`),
  createTask: (data) => api.post('/api-test/tasks', data),
}

export default api
