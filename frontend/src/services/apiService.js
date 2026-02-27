import axios from 'axios'
import { getInquira } from './generatedApi'
import { v1Api } from './contracts/v1Api'
import { parseSseBuffer } from '../utils/sseParser'
import { disableStreamingForUnsupportedStatus, isStreamingEnabled } from '../utils/streamingCapability'
import { inferTableNameFromDataPath } from '../utils/chatBootstrap'
import { normalizeExecutionResponse } from '../utils/runtimeExecution'

// ------------------------------------------------------------------
// GLOBAL AXIOS CONFIGURATION
// The generated client uses the global 'axios' instance.
// We configure it here to maintain our interceptor logic.
// ------------------------------------------------------------------

function getDefaultApiBase() {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000'
  }

  if (window.__TAURI_INTERNALS__) {
    // In packaged Tauri apps, window origin is tauri://localhost and is not the Python backend.
    return 'http://localhost:8000'
  }

  if (import.meta.env.DEV) {
    const { hostname } = window.location
    const port = '8000'
    // Force http protocol for backend as tauri:// won't reach Python server
    return `http://${hostname || 'localhost'}:${port}`
  }

  return 'http://localhost:8000'
}

const resolvedEnvBase = (import.meta.env.VITE_API_BASE || '').trim()
const apiBaseUrl = resolvedEnvBase || getDefaultApiBase()

// Configure GLOBAL axios defaults
axios.defaults.baseURL = apiBaseUrl
axios.defaults.timeout = 360000 // 6 minutes
axios.defaults.withCredentials = true
axios.defaults.headers.common['Content-Type'] = 'application/json'

// Request interceptor
axios.interceptors.request.use(
  (config) => {
    // Add any auth headers or other common headers here
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
axios.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const status = error?.response?.status
    const url = String(error?.config?.url || '')
    const isAuthProbe = url.includes('/api/v1/auth/me')
    const isExpectedAuthCheckFailure =
      (status === 401 || !status) &&
      (isAuthProbe || url.includes('/api/v1/auth/login') || url.includes('/api/v1/auth/logout'))

    if (!isExpectedAuthCheckFailure) {
      console.error('API Error:', error)
    }

    // Add more specific error information
    if (error.response) {
      // Server responded with error status
      error.status = error.response.status
      error.statusText = error.response.statusText
      error.data = error.response.data
    } else if (error.request) {
      // Network error
      error.code = 'NETWORK_ERROR'
      error.message = 'Network error - please check your connection'
    } else {
      // Other error
      error.code = 'UNKNOWN_ERROR'
      error.message = error.message || 'An unknown error occurred'
    }

    throw error
  }
)

// Initialize the generated client
const client = getInquira()

export const apiService = {
  // Authentication endpoints
  async register(username, password) {
    return client.registerUserAuthRegisterPost({ username, password })
  },

  async login(username, password) {
    return client.loginUserAuthLoginPost({ username, password })
  },

  async logout() {
    return client.logoutUserAuthLogoutPost()
  },

  async verifyAuth() {
    console.debug('🔍 Making verifyAuth request to /api/v1/auth/me')
    try {
      const result = await this.v1GetCurrentUser()
      console.debug('✅ verifyAuth success:', result)
      return result
    } catch (error) {
      console.error('❌ verifyAuth failed:', error.response?.status, error.response?.data)

      // In development, if backend is not available, allow the app to continue
      if (import.meta.env.DEV && error.code === 'NETWORK_ERROR') {
        console.warn('⚠️ Backend not available in development mode. Continuing without authentication.')
        // Return a mock authenticated user for development
        return {
          user: {
            user_id: 'dev-user',
            username: 'dev-user'
          }
        }
      }

      throw error
    }
  },

  async changePassword(currentPassword, newPassword, confirmPassword) {
    return client.changePasswordAuthChangePasswordPost({
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword
    })
  },

  async deleteAccount(confirmationText, currentPassword) {
    return client.deleteAccountAuthDeleteAccountDelete({
      confirmation_text: confirmationText,
      current_password: currentPassword
    })
  },

  // Settings management
  async getSettings() {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    return {
      api_key: null,
      api_key_present: !!appStore.apiKeyConfigured,
      data_path: appStore.schemaFileId || appStore.dataFilePath || null,
      context: appStore.schemaContext || '',
      table_name: appStore.ingestedTableName || null
    }
  },

  async getApiKey() {
    return client.viewApikeySettingsViewApiKeyGet()
  },

  // Check whether data/schema update is needed
  async checkUpdate() {
    return {
      should_update: false,
      reasons: [],
      dataset_updated_at: null
    }
  },

  async setDataPath(dataPath) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    appStore.setDataFilePath(dataPath || '')
    return { detail: 'Data path saved.' }
  },

  async setContext(context) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    appStore.setSchemaContext(context || '')
    return { detail: 'Context saved.' }
  },

  async setApiKeySettings(apiKey) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    await this.v1SetApiKey(apiKey || '')
    appStore.setApiKeyConfigured(true)
    return { detail: 'API key saved securely.' }
  },

  // Data preview
  async getDataPreview(sampleType = 'random') {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    if (!appStore.activeWorkspaceId || !appStore.ingestedTableName) {
      return {
        success: true,
        data: [],
        row_count: 0,
        sample_type: sampleType,
        message: 'Select a workspace dataset to preview.'
      }
    }
    return this.v1GetDatasetPreview(
      appStore.activeWorkspaceId,
      appStore.ingestedTableName,
      sampleType,
      100
    )
  },

  // Generate schema with context
  async generateSchema(filepath, context = null, forceRegenerate = false) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    const workspaceId = appStore.activeWorkspaceId
    const tableName = (appStore.ingestedTableName || inferTableNameFromDataPath(filepath || appStore.dataFilePath || '')).trim()
    if (!workspaceId || !tableName) {
      throw new Error('Select a workspace dataset before generating schema.')
    }
    if (forceRegenerate) {
      return this.v1RegenerateDatasetSchema(workspaceId, tableName, {
        context: context || ''
      })
    }
    const schema = await this.v1GetDatasetSchema(workspaceId, tableName)
    if (!context) return schema
    return this.v1SaveDatasetSchema(workspaceId, tableName, {
      context,
      columns: schema.columns || []
    })
  },

  /**
   * Generate schema descriptions from column metadata (browser-native flow).
   * The frontend sends columns from DuckDB-WASM directly — no file path needed.
   */
  async generateSchemaFromColumns(tableName, columns, context = null) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    if (!appStore.activeWorkspaceId) {
      throw new Error('Create/select a workspace before generating schema.')
    }
    return this.v1SaveDatasetSchema(appStore.activeWorkspaceId, tableName, {
      context: context || '',
      columns: (columns || []).map((col) => ({
        name: col.name,
        dtype: col.dtype || col.type || 'VARCHAR',
        description: col.description || '',
        samples: appStore.allowSchemaSampleValues && Array.isArray(col.samples) ? col.samples : []
      }))
    })
  },

  // Load existing schema
  async loadSchema(filepath) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    const workspaceId = appStore.activeWorkspaceId
    const tableName = (appStore.ingestedTableName || inferTableNameFromDataPath(filepath || appStore.dataFilePath || '')).trim()
    if (!workspaceId || !tableName) {
      throw new Error('Select a workspace dataset before loading schema.')
    }
    return this.v1GetDatasetSchema(workspaceId, tableName)
  },

  // Save schema
  async saveSchema(filepath, context, columns) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    const workspaceId = appStore.activeWorkspaceId
    const tableName = (appStore.ingestedTableName || inferTableNameFromDataPath(filepath || appStore.dataFilePath || '')).trim()
    if (!workspaceId || !tableName) {
      throw new Error('Select a workspace dataset before saving schema.')
    }
    return this.v1SaveDatasetSchema(workspaceId, tableName, { context, columns })
  },

  // List schemas
  async listSchemas() {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    if (!appStore.activeWorkspaceId) return { schemas: [] }
    return this.v1ListSchemas(appStore.activeWorkspaceId)
  },

  // Get database and schema paths
  async getDatabasePaths() {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    if (!appStore.activeWorkspaceId) {
      return { database_path: null, schema_path: null, base_directory: null }
    }
    const paths = await this.v1GetWorkspacePaths(appStore.activeWorkspaceId)
    return {
      database_path: paths?.duckdb_path || null,
      schema_path: paths?.workspace_dir || null,
      base_directory: paths?.workspace_dir || null
    }
  },

  // Code execution (server-side)
  async executeCode(code, timeout = 60, workspaceId = null) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    const activeWorkspaceId = workspaceId || appStore.activeWorkspaceId
    if (!activeWorkspaceId) {
      throw new Error('Create/select a workspace before running code.')
    }
    console.debug('🚀 [API] Executing code...', { timeout })
    const response = await fetch(
      `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${activeWorkspaceId}/execute`,
      {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ code, timeout })
      }
    )
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(detail.detail || `Execution request failed (${response.status})`)
    }
    const payload = await response.json()
    return normalizeExecutionResponse(payload)
  },

  // File data loading — inspect file for columns, then trigger background DuckDB conversion
  async uploadDataPath(filePath) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    if (!appStore.activeWorkspaceId) {
      throw new Error('Create/select a workspace before loading a dataset.')
    }

    const ds = await this.v1AddDataset(appStore.activeWorkspaceId, filePath)
    let columns = []
    try {
      const schema = await this.v1GetDatasetSchema(appStore.activeWorkspaceId, ds.table_name)
      columns = (schema?.columns || []).map((col) => ({
        name: col.name,
        type: col.dtype || col.type || 'VARCHAR',
        dtype: col.dtype || col.type || 'VARCHAR',
        description: col.description || '',
        samples: Array.isArray(col.samples) ? col.samples : []
      }))
    } catch (_error) {
      // Keep ingestion successful even if schema metadata is unavailable.
    }

    return {
      table_name: ds.table_name,
      row_count: ds.row_count ?? null,
      file_path: ds.source_path || filePath,
      columns
    }
  },

  // Browser fallback — same endpoint, uses file name as path
  async uploadFile(file) {
    throw new Error('Browser file uploads are not supported in v1 desktop mode. Use the native file picker.')
  },

  // Chat and analysis
  async analyzeData(data, signal = null) {
    throw new Error('Legacy /chat endpoint removed. Use v1Analyze with workspace scope.')
  },

  async analyzeDataStream(data, { signal = null, onEvent = null } = {}) {
    throw new Error('Legacy /chat/stream endpoint removed. Use v1AnalyzeStream with workspace scope.')
  },

  async getHistory() {
    return client.getChatHistoryHistoryGet()
  },

  // Health check
  async healthCheck() {
    return { status: 'ok' }
  },

  // test gemini api
  async testGeminiApi(apiKey, model = '') {
    const payload = { api_key: apiKey, model: model || undefined }
    try {
      // Prefer generated endpoint names from both old and current OpenAPI specs.
      const generatedCall =
        client.testGeminiApiKeyApiV1AdminTestGeminiPost || client.testGeminiApiKeyApiTestGeminiPost
      if (typeof generatedCall === 'function') {
        return generatedCall(payload)
      }

      return axios.post('/api/v1/admin/test-gemini', payload)
    } catch (error) {
      // Fallback to v1 admin route when backend omits legacy route.
      if (error?.response?.status === 404) {
        return axios.post('/api/v1/admin/test-gemini', payload)
      }
      throw error
    }
  },

  // System utilities
  async openFileDialog() {
    // Opens a native OS file picker via backend and returns { data_path }
    try {
      const response = await client.openFileDialogSystemOpenFileDialogPost()
      return response
    } catch (error) {
      throw error
    }
  },

  // Dataset management
  async listDatasets() {
    try {
      const response = await client.listUserDatasetsDatasetsListGet()
      console.debug('📋 [API] Datasets loaded:', response)
      return response
    } catch (error) {
      console.error('Failed to list datasets:', error)
      return []
    }
  },

  async setDataPathSimple(dataPath) {
    const { useAppStore } = await import('../stores/appStore')
    const appStore = useAppStore()
    appStore.setDataFilePath(dataPath || '')
    return { detail: 'Data path saved locally.' }
  },

  async checkDatasetHealth(tableName) {
    try {
      const response = await client.checkDatasetHealthDatasetsHealthTableNameGet(tableName)
      return response
    } catch (error) {
      console.error('Failed to check dataset health:', error)
      throw error
    }
  },

  async deleteDataset(tableName) {
    try {
      // Use direct axios call to avoid issues with generated client update
      const response = await axios.delete(`/datasets/${tableName}`)
      return response
    } catch (error) {
      console.error('Failed to delete dataset:', error)
      throw error
    }
  },

  async refreshDataset(tableName, regenerateSchema = true) {
    try {
      console.debug(`🔄 [API] Refreshing dataset: ${tableName}`)
      const response = await axios.post(`/datasets/${tableName}/refresh`, {
        regenerate_schema: regenerateSchema
      })
      console.debug('✅ [API] Dataset refreshed:', response)
      return response
    } catch (error) {
      console.error('Failed to refresh dataset:', error)
      throw error
    }
  },

  async downloadDatasetBlob(tableName) {
    try {
      const response = await axios.get(`/datasets/${tableName}/download`, {
        responseType: 'blob'
      })
      return response
    } catch (error) {
      console.error('Failed to download dataset blob:', error)
      throw error
    }
  },

  // V1 Workspace APIs
  async v1ListWorkspaces() {
    return v1Api.workspaces.list()
  },

  async v1CreateWorkspace(name) {
    return v1Api.workspaces.create(name)
  },

  async v1ActivateWorkspace(workspaceId) {
    return v1Api.workspaces.activate(workspaceId)
  },

  async v1DeleteWorkspace(workspaceId) {
    return v1Api.workspaces.remove(workspaceId)
  },

  async v1ListWorkspaceDeletionJobs() {
    return v1Api.workspaces.deletions()
  },

  async v1GetWorkspaceDeletionJob(jobId) {
    return v1Api.workspaces.deletionById(jobId)
  },

  async v1ListDatasets(workspaceId) {
    return v1Api.datasets.list(workspaceId)
  },

  async v1GetPreferences() {
    return v1Api.preferences.get()
  },

  async v1UpdatePreferences(payload) {
    return v1Api.preferences.update(payload)
  },

  async v1SetApiKey(apiKey) {
    return v1Api.preferences.setApiKey(apiKey)
  },

  async v1DeleteApiKey() {
    return v1Api.preferences.deleteApiKey()
  },

  async v1GetWorkspacePaths(workspaceId) {
    return axios.get(`/api/v1/workspaces/${workspaceId}/paths`)
  },

  async v1AddDataset(workspaceId, sourcePath) {
    return v1Api.datasets.add(workspaceId, sourcePath)
  },

  async v1GetDatasetSchema(workspaceId, tableName) {
    return axios.get(`/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema`)
  },

  async v1SaveDatasetSchema(workspaceId, tableName, payload) {
    return axios.post(`/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema`, payload)
  },

  async v1RegenerateDatasetSchema(workspaceId, tableName, payload = {}) {
    return axios.post(
      `/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema/regenerate`,
      payload
    )
  },

  async v1ListSchemas(workspaceId) {
    return axios.get(`/api/v1/workspaces/${workspaceId}/schemas`)
  },

  async v1GetDatasetPreview(workspaceId, tableName, sampleType = 'random', limit = 100) {
    return axios.get(`/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/preview`, {
      params: { sample_type: sampleType, limit }
    })
  },

  async v1SyncBrowserDataset(workspaceId, payload) {
    return v1Api.datasets.syncBrowser(workspaceId, payload)
  },

  async v1ListConversations(workspaceId, limit = 50) {
    return v1Api.conversations.list(workspaceId, limit)
  },

  async v1CreateConversation(workspaceId, title = null) {
    return v1Api.conversations.create(workspaceId, title)
  },

  async v1ClearConversation(conversationId) {
    return v1Api.conversations.clear(conversationId)
  },

  async v1DeleteConversation(conversationId) {
    return v1Api.conversations.remove(conversationId)
  },

  async v1UpdateConversation(conversationId, title) {
    return v1Api.conversations.update(conversationId, { title })
  },

  async v1ListTurns(conversationId, limit = 5, before = null) {
    const params = { limit }
    if (before) params.before = before
    return v1Api.conversations.turns(conversationId, params)
  },

  async v1Analyze(payload) {
    return v1Api.chat.analyze(payload)
  },

  async v1InstallRunnerPackage(payload) {
    return v1Api.runtime.installRunnerPackage(payload)
  },

  async v1AnalyzeStream(payload, { signal = null, onEvent = null } = {}) {
    if (!isStreamingEnabled()) {
      return this.v1Analyze(payload)
    }

    const url = `${apiBaseUrl.replace(/\/+$/, '')}${v1Api.chat.stream}`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify(payload),
      signal
    })

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`
      try {
        const text = await response.text()
        if (text) detail = text
      } catch (_) {
        // keep default
      }
      const err = new Error(detail)
      err.status = response.status
      disableStreamingForUnsupportedStatus(response.status)
      throw err
    }

    if (!response.body) {
      throw new Error('Streaming not supported by browser/runtime.')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalPayload = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const { events, remainder } = parseSseBuffer(buffer)
      buffer = remainder

      for (const evt of events) {
        if (onEvent) onEvent(evt)
        if (evt.event === 'final') {
          finalPayload = evt.data
        } else if (evt.event === 'error') {
          const detail = evt.data?.detail || 'Streaming analysis failed.'
          const err = new Error(detail)
          err.status = evt.data?.status_code || 500
          throw err
        }
      }
    }

    if (!finalPayload) {
      throw new Error('Stream ended without final analysis payload.')
    }
    return finalPayload
  },

  async v1GetCurrentUser() {
    return v1Api.auth.me()
  },

  async v1Register(username, password) {
    return v1Api.auth.register(username, password)
  },

  async v1Login(username, password) {
    return v1Api.auth.login(username, password)
  },

  async v1Logout() {
    return v1Api.auth.logout()
  }
}

export default apiService
