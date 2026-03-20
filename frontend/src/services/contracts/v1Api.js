import axios from 'axios'

/**
 * Contract wrapper layer with stable, concise names.
 * This sits on top of the OpenAPI-generated client surface.
 */
export const v1Api = {
  auth: {
    me: (config = {}) => axios.get('/api/v1/auth/me', config),
    register: (username, password) => axios.post('/api/v1/auth/register', { username, password }),
    login: (username, password) => axios.post('/api/v1/auth/login', { username, password }),
    logout: () => axios.post('/api/v1/auth/logout')
  },
  workspaces: {
    list: () => axios.get('/api/v1/workspaces'),
    create: (name) => axios.post('/api/v1/workspaces', { name }),
    activate: (workspaceId) => axios.put(`/api/v1/workspaces/${workspaceId}/activate`),
    rename: (workspaceId, name) => axios.patch(`/api/v1/workspaces/${workspaceId}`, { name }),
    clearDatabase: (workspaceId) => axios.post(`/api/v1/workspaces/${workspaceId}/database/clear`),
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
  preferences: {
    get: () => axios.get('/api/v1/preferences'),
    update: (payload) => axios.put('/api/v1/preferences', payload),
    refreshModels: (payload) => axios.post('/api/v1/preferences/models/refresh', payload),
    setApiKey: (apiKey, provider = 'openrouter') =>
      axios.put('/api/v1/preferences/api-key', { api_key: apiKey, provider }),
    deleteApiKey: (provider = 'openrouter') =>
      axios.delete('/api/v1/preferences/api-key', { params: { provider } })
  },
  conversations: {
    list: (workspaceId, limit = 50) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/conversations`, { params: { limit } }),
    create: (workspaceId, title = null) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/conversations`, { title }),
    clear: (conversationId) => axios.post(`/api/v1/conversations/${conversationId}/clear`),
    remove: (conversationId) => axios.delete(`/api/v1/conversations/${conversationId}`),
    update: (conversationId, payload) => axios.patch(`/api/v1/conversations/${conversationId}`, payload),
    turns: (conversationId, params) => axios.get(`/api/v1/conversations/${conversationId}/turns`, { params })
  },
  chat: {
    analyze: (payload) => axios.post('/api/v1/chat/analyze', payload),
    stream: '/api/v1/chat/stream',
    respondIntervention: (interventionId, payload) =>
      axios.post(`/api/v1/chat/interventions/${interventionId}/response`, payload)
  },
  runtime: {
    installRunnerPackage: (payload) =>
      axios.post('/api/v1/runtime/runner/packages/install', payload),
    workspaceColumns: (workspaceId) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/columns`),
    listWorkspaceCommands: (workspaceId) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/commands`),
    executeWorkspaceCommand: (workspaceId, payload) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/commands/execute`, payload),
    bootstrapWorkspaceRuntime: (workspaceId) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/runtime/bootstrap`),
    kernelStatus: (workspaceId) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/kernel/status`),
    kernelInterrupt: (workspaceId) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/kernel/interrupt`),
    kernelReset: (workspaceId) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/kernel/reset`),
    kernelRestart: (workspaceId) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/kernel/restart`)
  }
}

export default v1Api
