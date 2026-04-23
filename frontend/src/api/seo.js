import api from './index'

export const seoApi = {
  list: (params) => api.get('/seo/tasks', { params }),
  get: (id) => api.get(`/seo/tasks/${id}`),
  create: (data) => api.post('/seo/tasks', data),
  delete: (id) => api.delete(`/seo/tasks/${id}`),
  run: (id) => api.post(`/seo/tasks/${id}/run`),
  getIssues: (id, severity) => api.get(`/seo/tasks/${id}/issues`, { params: severity ? { severity } : {} }),
  getReport: (id) => api.get(`/seo/tasks/${id}/report`),
}