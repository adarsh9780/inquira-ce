import axios from 'axios'
import { getInquira } from './generatedApi'

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
    console.log('🔍 Making verifyAuth request to /auth/verify')
    try {
      const result = await client.verifyAuthAuthVerifyGet()
      console.log('✅ verifyAuth success:', result)
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
    console.log('📤 [API] Setting data path:', dataPath)

    // First verify authentication
    try {
      console.log('🔐 [API] Verifying authentication...')
      await this.verifyAuth()
      console.log('✅ [API] Authentication verified')
    } catch (authError) {
      console.error('❌ [API] Authentication failed:', authError.response?.data)
      throw new Error('Authentication required. Please log in first.')
    }

    try {
      const response = await client.setDataPathSettingsSetDataPathPut({ data_path: dataPath })
      console.log('✅ [API] Data path set successfully:', response)
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
  async generateSchema(filepath, context = null) {
    console.log('🔄 Generating schema for:', filepath)

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
        context: context
      })
      console.log('✅ Schema generation successful')
      return response
    } catch (error) {
      console.error('❌ Schema generation failed:', error.response?.data)
      throw error
    }
  },

  // Load existing schema
  async loadSchema(filepath) {
    console.log('📂 Loading schema for:', filepath)

    // Verify authentication before loading schema
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for schema loading')
      throw new Error('Authentication required for schema loading')
    }

    try {
      // NOTE: generated function takes filepath as an argument, separate from options
      const response = await client.loadSchemaEndpointSchemasLoadFilepathGet(encodeURIComponent(filepath))
      console.log('✅ Schema loading successful')
      return response
    } catch (error) {
      console.error('❌ Schema loading failed:', error.response?.data)
      throw error
    }
  },

  // Save schema
  async saveSchema(filepath, context, columns) {
    console.log('💾 Saving schema for:', filepath)

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
      console.log('✅ Schema saving successful')
      return response
    } catch (error) {
      console.error('❌ Schema saving failed:', error.response?.data)
      throw error
    }
  },

  // List schemas
  async listSchemas() {
    console.log('📋 Listing schemas')

    // Verify authentication before listing schemas
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for schema listing')
      throw new Error('Authentication required for schema listing')
    }

    try {
      const response = await client.listSchemasEndpointSchemasListGet()
      console.log('✅ Schema listing successful')
      return response
    } catch (error) {
      console.error('❌ Schema listing failed:', error.response?.data)
      throw error
    }
  },

  // Get database and schema paths
  async getDatabasePaths() {
    console.log('📂 Getting database paths')

    // Verify authentication before getting paths
    try {
      await this.verifyAuth()
    } catch (authError) {
      console.error('❌ Authentication failed for getting database paths')
      throw new Error('Authentication required for getting database paths')
    }

    try {
      const response = await client.getStoragePathsSettingsPathsGet()
      console.log('✅ Database paths retrieved successfully')
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

  async getHistory() {
    return client.getChatHistoryHistoryGet()
  },

  // Code execution
  async executeCode(code) {
    // using the 'with-variables' endpoint as in original service
    return client.executeCodeWithVariablesExecuteWithVariablesPost({ code: code })
  },

  // Health check
  async healthCheck() {
    console.log('🏥 [API] Checking backend health...')
    try {
      const response = await client.rootGet()
      console.log('✅ [API] Backend is healthy:', response)
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
  }
}

export default apiService
