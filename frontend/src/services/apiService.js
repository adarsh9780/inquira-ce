import axios from 'axios'
import { getInquira } from './generatedApi'
import { parseSseBuffer } from '../utils/sseParser'
import { disableStreamingForUnsupportedStatus, isStreamingEnabled } from '../utils/streamingCapability'

// ------------------------------------------------------------------
// GLOBAL AXIOS CONFIGURATION
// The generated client uses the global 'axios' instance.
// We configure it here to maintain our interceptor logic.
// ------------------------------------------------------------------

function getDefaultApiBase() {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000'
  }

  if (import.meta.env.DEV) {
    const { protocol, hostname } = window.location
    const port = '8000'
    return `${protocol}//${hostname}:${port}`
  }

  return window.location.origin
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
    console.error('API Error:', error)

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
    console.debug('🔍 Making verifyAuth request to /auth/verify')
    try {
      const result = await client.verifyAuthAuthVerifyGet()
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
    return client.viewAllSettingsSettingsViewGet()
  },

  async getApiKey() {
    return client.viewApikeySettingsViewApiKeyGet()
  },

  // Check whether data/schema update is needed
  async checkUpdate() {
    return client.checkUpdateNeededSettingsCheckUpdateGet()
  },

  async setDataPath(dataPath) {
    console.debug('📤 [API] Setting data path:', dataPath)

    // First verify authentication
    try {
      console.debug('🔐 [API] Verifying authentication...')
      await this.verifyAuth()
      console.debug('✅ [API] Authentication verified')
    } catch (authError) {
      console.error('❌ [API] Authentication failed:', authError.response?.data)
      throw new Error('Authentication required. Please log in first.')
    }

    try {
      const response = await client.setDataPathSettingsSetDataPathPut({ data_path: dataPath })
      console.debug('✅ [API] Data path set successfully:', response)
      return response
    } catch (error) {
      console.error('❌ [API] Failed to set data path:', error.response?.data)

      // Provide more specific error messages
      if (error.response?.status === 401) {
        throw new Error('Authentication expired. Please log in again.')
      } else if (error.response?.status === 403) {
        throw new Error('Access denied. You may not have permission to save settings.')
      } else if (error.response?.status === 400) {
        const errorDetail = error.response?.data?.detail || 'Invalid request data'
        throw new Error(`Bad request: ${errorDetail}`)
      }

      throw error
    }
  },

  async setContext(context) {
    return client.setContextSettingsSetContextPut({ context: context })
  },

  async setApiKeySettings(apiKey) {
    return client.setApikeySettingsSetApiKeyPut({ api_key: apiKey })
  },

  // Data preview
  async getDataPreview(sampleType = 'random') {
    return client.getDataPreviewDataPreviewGet({ sample_type: sampleType })
  },

  // Generate schema with context
  async generateSchema(filepath, context = null, forceRegenerate = false) {
    console.debug('🔄 Generating schema for:', filepath, 'force:', forceRegenerate)

    // Verify authentication before schema generation
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for schema generation')
      throw new Error('Authentication required for schema generation')
    }

    try {
      const response = await client.generateSchemaSchemasGeneratePost({
        filepath: filepath,
        context: context,
        force_regenerate: forceRegenerate
      })
      console.debug('✅ Schema generation successful')
      return response
    } catch (error) {
      console.error('❌ Schema generation failed:', error.response?.data)
      throw error
    }
  },

  /**
   * Generate schema descriptions from column metadata (browser-native flow).
   * The frontend sends columns from DuckDB-WASM directly — no file path needed.
   */
  async generateSchemaFromColumns(tableName, columns, context = null) {
    console.debug('🔄 Generating schema from columns for table:', tableName)

    try {
      await this.verifyAuth()
    } catch (authError) {
      throw new Error('Authentication required for schema generation')
    }

    try {
      const { default: axios } = await import('axios')
      const baseUrl = client.defaults?.baseURL || (import.meta.env.VITE_API_BASE || '')
      const response = await axios.post(`${baseUrl}/schemas/generate-from-columns`, {
        table_name: tableName,
        columns: columns,
        context: context
      }, {
        withCredentials: true
      })
      console.debug('✅ Schema from columns generation successful')
      return response.data
    } catch (error) {
      console.error('❌ Schema from columns generation failed:', error.response?.data)
      throw error
    }
  },

  // Load existing schema
  async loadSchema(filepath) {
    console.debug('📂 Loading schema for:', filepath)

    // Verify authentication before loading schema
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for schema loading')
      throw new Error('Authentication required for schema loading')
    }

    try {
      // NOTE: generated function takes filepath as an argument, separate from options
      const response = await client.loadSchemaEndpointSchemasLoadFilepathGet(filepath)
      console.debug('✅ Schema loading successful')
      return response
    } catch (error) {
      console.error('❌ Schema loading failed:', error.response?.data)
      throw error
    }
  },

  // Save schema
  async saveSchema(filepath, context, columns) {
    console.debug('💾 Saving schema for:', filepath)

    // Verify authentication before saving schema
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for schema saving')
      throw new Error('Authentication required for schema saving')
    }

    try {
      const response = await client.saveSchemaEndpointSchemasSavePost({
        filepath: filepath,
        context: context,
        columns: columns
      })
      console.debug('✅ Schema saving successful')
      return response
    } catch (error) {
      console.error('❌ Schema saving failed:', error.response?.data)
      throw error
    }
  },

  // List schemas
  async listSchemas() {
    console.debug('📋 Listing schemas')

    // Verify authentication before listing schemas
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for schema listing')
      throw new Error('Authentication required for schema listing')
    }

    try {
      const response = await client.listSchemasEndpointSchemasListGet()
      console.debug('✅ Schema listing successful')
      return response
    } catch (error) {
      console.error('❌ Schema listing failed:', error.response?.data)
      throw error
    }
  },

  // Get database and schema paths
  async getDatabasePaths() {
    console.debug('📂 Getting database paths')

    // Verify authentication before getting paths
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for getting database paths')
      throw new Error('Authentication required for getting database paths')
    }

    try {
      const response = await client.getStoragePathsSettingsPathsGet()
      console.debug('✅ Database paths retrieved successfully')
      return response
    } catch (error) {
      console.error('❌ Failed to get database paths:', error.response?.data)
      throw error
    }
  },

  // Chat and analysis
  async analyzeData(data, signal = null) {
    // data is typically { question, context, model, current_code }
    return client.chatEndpointChatPost(data, { signal })
  },

  async analyzeDataStream(data, { signal = null, onEvent = null } = {}) {
    if (!isStreamingEnabled()) {
      return this.analyzeData(data, signal)
    }

    const url = `${apiBaseUrl.replace(/\/+$/, '')}/chat/stream`
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      credentials: 'include',
      body: JSON.stringify(data),
      signal
    })

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`
      try {
        const text = await response.text()
        if (text) detail = text
      } catch (_) {
        // keep default detail
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

  async getHistory() {
    return client.getChatHistoryHistoryGet()
  },

  // Health check
  async healthCheck() {
    console.debug('🏥 [API] Checking backend health...')
    try {
      const response = await client.rootGet()
      console.debug('✅ [API] Backend is healthy:', response)
      return response
    } catch (error) {
      console.error('❌ [API] Backend health check failed:', error.response?.status)
      throw error
    }
  },

  // test gemini api
  async testGeminiApi(apiKey) {
    return client.testGeminiApiKeyApiTestGeminiPost({ api_key: apiKey })
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
    // Set data path without triggering reprocessing
    try {
      const response = await client.setDataPathSimpleSettingsSetDataPathSimplePut({ data_path: dataPath })
      return response
    } catch (error) {
      console.error('Failed to set data path (simple):', error)
      throw error
    }
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
  }
}

export default apiService
