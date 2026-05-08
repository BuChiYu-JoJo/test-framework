import { defineStore } from 'pinia'
import { ref } from 'vue'
import { projectsApi } from '../api'

export const useProjectsStore = defineStore('projects', () => {
  const projects = ref([])
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      projects.value = await projectsApi.list()
    } finally {
      loading.value = false
    }
  }

  async function createProject(data) {
    await projectsApi.create(data)
    await fetchProjects()
  }

  async function updateProject(id, data) {
    await projectsApi.update(id, data)
    await fetchProjects()
  }

  async function deleteProject(id) {
    await projectsApi.delete(id)
    await fetchProjects()
  }

  return { projects, loading, fetchProjects, createProject, updateProject, deleteProject }
})
