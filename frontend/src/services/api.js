import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Projects
export const listProjects = () => api.get('/projects/').then(r => r.data)
export const getProject = (id) => api.get(`/projects/${id}`).then(r => r.data)
export const createProject = (data) => api.post('/projects/', data).then(r => r.data)
export const updateProject = (id, data) => api.patch(`/projects/${id}`, data).then(r => r.data)
export const deleteProject = (id) => api.delete(`/projects/${id}`).then(r => r.data)

// Sources
export const listSources = (projectId) => api.get(`/sources/project/${projectId}`).then(r => r.data)
export const pasteSource = (projectId, data) => api.post(`/sources/paste?project_id=${projectId}`, data).then(r => r.data)
export const uploadSource = (projectId, formData) => api.post(`/sources/upload`, formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
}).then(r => r.data)
export const deleteSource = (id) => api.delete(`/sources/${id}`).then(r => r.data)

// Analysis
export const getPhaseState = (projectId, phaseNumber) => api.get(`/analysis/phase-state/${projectId}/${phaseNumber}`).then(r => r.data)
export const sendPhaseChat = (data) => api.post('/analysis/chat', data).then(r => r.data)
export const advancePhase = (projectId) => api.post(`/analysis/advance-phase/${projectId}`).then(r => r.data)
export const generateReport = (projectId, format = 'pdf') => api.post(`/analysis/generate-report/${projectId}?format=${format}`).then(r => r.data)
export const listReports = (projectId) => api.get(`/analysis/reports/${projectId}`).then(r => r.data)

export default api
