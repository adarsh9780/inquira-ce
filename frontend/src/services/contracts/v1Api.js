import axios from 'axios'

/**
 * Contract wrapper layer with stable, concise names.
 * This sits on top of the OpenAPI-generated client surface.
 */
export const v1Api = {
  auth: {
    me: () => axios.get('/api/v1/auth/me'),
    register: (username, password) => axios.post('/api/v1/auth/register', { username, password }),
    login: (username, password) => axios.post('/api/v1/auth/login', { username, password }),
    logout: () => axios.post('/api/v1/auth/logout')
  },
  workspaces: {
    list: () => axios.get('/api/v1/workspaces'),
    create: (name) => axios.post('/api/v1/workspaces', { name }),
    activate: (workspaceId) => axios.put(`/api/v1/workspaces/${workspaceId}/activate`),
    remove: (workspaceId) => axios.delete(`/api/v1/workspaces/${workspaceId}`),
    deletions: () => axios.get('/api/v1/workspaces/deletions'),
    deletionById: (jobId) => axios.get(`/api/v1/workspaces/deletions/${jobId}`)
  },
  datasets: {
    list: (workspaceId) => axios.get(`/api/v1/workspaces/${workspaceId}/datasets`),
    add: (workspaceId, sourcePath) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/datasets`, { source_path: sourcePath }),
    syncBrowser: (workspaceId, payload) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/datasets/browser-sync`, payload)
  },
  conversations: {
    list: (workspaceId, limit = 50) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/conversations`, { params: { limit } }),
    create: (workspaceId, title = null) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/conversations`, { title }),
    clear: (conversationId) => axios.post(`/api/v1/conversations/${conversationId}/clear`),
    remove: (conversationId) => axios.delete(`/api/v1/conversations/${conversationId}`),
    turns: (conversationId, params) => axios.get(`/api/v1/conversations/${conversationId}/turns`, { params })
  },
  chat: {
    analyze: (payload) => axios.post('/api/v1/chat/analyze', payload)
  }
}

export default v1Api
