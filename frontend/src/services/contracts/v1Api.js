import axios from 'axios'

/**
 * Contract wrapper layer with stable, concise names.
 * This sits on top of the OpenAPI-generated client surface.
 */
export const v1Api = {
  auth: {
    config: () => axios.get('/api/v1/auth/config'),
    me: (config = {}) => axios.get('/api/v1/auth/me', config),
    logout: () => axios.post('/api/v1/auth/logout')
  },
  workspaces: {
    list: () => axios.get('/api/v1/workspaces'),
    create: (name, schemaContext = '') => axios.post('/api/v1/workspaces', {
      name,
      schema_context: schemaContext,
    }),
    activate: (workspaceId) => axios.put(`/api/v1/workspaces/${workspaceId}/activate`),
    summary: (workspaceId) => axios.get(`/api/v1/workspaces/${workspaceId}/summary`),
    rename: (workspaceId, name, schemaContext = undefined) => {
      const payload = {}
      if (name !== null && name !== undefined) payload.name = name
      if (schemaContext !== undefined) payload.schema_context = schemaContext
      return axios.patch(`/api/v1/workspaces/${workspaceId}`, payload)
    },
    clearDatabase: (workspaceId) => axios.post(`/api/v1/workspaces/${workspaceId}/database/clear`),
    remove: (workspaceId) => axios.delete(`/api/v1/workspaces/${workspaceId}`),
    deletions: () => axios.get('/api/v1/workspaces/deletions'),
    deletionById: (jobId) => axios.get(`/api/v1/workspaces/deletions/${jobId}`)
  },
  datasets: {
    list: (workspaceId) => axios.get(`/api/v1/workspaces/${workspaceId}/datasets`),
    add: (workspaceId, sourcePath) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/datasets`, { source_path: sourcePath }),
    addBatch: (workspaceId, sourcePaths) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/datasets/batch`, { source_paths: sourcePaths }),
    remove: (workspaceId, tableName) =>
      axios.delete(`/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}`),
    ingestions: (workspaceId) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/datasets/ingestions`),
    ingestionById: (workspaceId, jobId) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/datasets/ingestions/${jobId}`),
    deletions: (workspaceId) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/datasets/deletions`),
    deletionById: (workspaceId, jobId) =>
      axios.get(`/api/v1/workspaces/${workspaceId}/datasets/deletions/${jobId}`),
    syncBrowser: (workspaceId, payload) =>
      axios.post(`/api/v1/workspaces/${workspaceId}/datasets/browser-sync`, payload)
  },
  preferences: {
    get: (provider = null) => axios.get('/api/v1/preferences', {
      params: provider ? { provider } : undefined,
    }),
    update: (payload) => axios.put('/api/v1/preferences', payload),
    refreshModels: (payload) => axios.post('/api/v1/preferences/models/refresh', payload),
    searchModels: ({ provider, query, limit = 25 }) =>
      axios.get('/api/v1/preferences/models/search', {
        params: {
          provider,
          q: query,
          limit,
        },
      }),
    verifyKey: (provider, apiKey) =>
      axios.post('/api/v1/preferences/verify-key', { provider, api_key: apiKey }),
    setApiKey: (payload) =>
      axios.put('/api/v1/preferences/api-key', payload),
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
