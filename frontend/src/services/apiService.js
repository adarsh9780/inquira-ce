import axios from 'axios'
import { getInquira } from './generatedApi'
import { v1Api } from './contracts/v1Api'
import { parseSseBuffer } from '../utils/sseParser'
import { inferTableNameFromDataPath } from '../utils/chatBootstrap'
import { normalizeExecutionResponse } from '../utils/runtimeExecution'
import { extractApiErrorMessage } from '../utils/apiError'
import { useAppStore } from '../stores/appStore'
import { invoke } from '@tauri-apps/api/core'
import { EventsOn } from '../../wailsjs/runtime/runtime'


// ------------------------------------------------------------------
// GLOBAL AXIOS CONFIGURATION
// The generated client uses the global 'axios' instance.
// We configure it here to maintain our interceptor logic.
// ------------------------------------------------------------------

function getDefaultApiBase() {
  if (typeof window === 'undefined') {
    return 'http://127.0.0.1:8000'
  }

  if (window.__TAURI_INTERNALS__) {
    // Use a numeric loopback address so desktop startup does not depend on localhost IPv6 resolution.
    return 'http://127.0.0.1:8000'
  }

  if (import.meta.env.DEV) {
    const { hostname } = window.location
    const port = '8000'
    // Force http protocol for backend as tauri:// won't reach Python server
    const resolvedHost = hostname === 'localhost' ? '127.0.0.1' : (hostname || '127.0.0.1')
    return `http://${resolvedHost}:${port}`
  }

  return 'http://127.0.0.1:8000'
}

function nativeWailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function normalizeNativeTurn(turn) {
  if (!turn || typeof turn !== 'object') return turn
  const parse = (value, fallback) => {
    if (typeof value !== 'string' || !value.trim()) return fallback
    try { return JSON.parse(value) } catch (_error) { return fallback }
  }
  return {
    ...turn,
    metadata: parse(turn.metadata_json, {}),
    tool_events: parse(turn.tool_events_json, []),
    result: parse(turn.result_json, null),
  }
}

function nativeTurnTree(turns) {
  const normalized = (Array.isArray(turns) ? turns : []).map(normalizeNativeTurn)
  const nodes = new Map(normalized.map((turn) => [String(turn.id), {
    ...turn,
    display_no: Number(turn.sequence || 0),
    children: [],
  }]))
  const roots = []
  for (const turn of normalized) {
    const node = nodes.get(String(turn.id))
    const parent = turn.parent_turn_id ? nodes.get(String(turn.parent_turn_id)) : null
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  const compare = (left, right) => Number(left?.sibling_order || 0) - Number(right?.sibling_order || 0) || Number(left?.sequence || 0) - Number(right?.sequence || 0)
  roots.sort(compare)
  for (const node of nodes.values()) node.children.sort(compare)
  return { turns: normalized, roots }
}

function nativeStatusMessage(stage) {
  return ({
    reading_schema: 'Reading the workspace schema…',
    generating: 'Writing analysis code…',
    executing: 'Running analysis code…',
    retrying: 'Correcting the analysis…',
    explaining: 'Explaining the result…',
    completed: 'Analysis complete.',
  })[String(stage || '')] || 'Working on the analysis…'
}

function normalizeNativeAnalysis(raw) {
  const execution = raw?.execution && typeof raw.execution === 'object' ? raw.execution : {}
  const publishedArtifacts = (Array.isArray(raw?.artifacts) ? raw.artifacts : []).map((artifact) => ({
    ...artifact,
    artifact_id: String(artifact?.artifact_id || artifact?.id || ''),
  }))
  let result = execution.result ?? null
  if (String(execution.result_kind || '').toLowerCase() === 'dataframe' && result && Array.isArray(result.rows)) {
    result = { ...result, data: result.rows, row_count: result.rows.length }
  }
  return {
    conversation_id: String(raw?.conversation?.id || ''),
    turn_id: String(raw?.turn?.id || ''),
    is_safe: execution.success !== false,
    is_relevant: true,
    code: String(raw?.code || ''),
    explanation: String(raw?.answer || ''),
    result_explanation: String(raw?.answer || ''),
    code_explanation: '',
    run_id: String(raw?.run_id || ''),
    execution: { ...execution, run_id: String(raw?.run_id || ''), artifacts: publishedArtifacts },
    result,
    result_kind: execution.result_kind || '',
    artifacts: publishedArtifacts,
    route: String(raw?.route || ''),
    metadata: raw?.metadata && typeof raw.metadata === 'object' ? { ...raw.metadata } : {},
  }
}

function normalizeNativeManualExecution(raw) {
  const execution = raw?.execution && typeof raw.execution === 'object' ? { ...raw.execution } : {}
  execution.artifacts = (Array.isArray(execution.artifacts) ? execution.artifacts : []).map((artifact) => ({
    ...artifact,
    artifact_id: String(artifact?.artifact_id || artifact?.id || ''),
  }))
  if (String(execution.result_kind || '').toLowerCase() === 'dataframe' && execution.result && Array.isArray(execution.result.rows)) {
    execution.result = { ...execution.result, data: execution.result.rows }
  }
  return {
    ...normalizeExecutionResponse(execution),
    conversation_id: String(raw?.conversation?.id || ''),
    turn_id: String(raw?.turn?.id || ''),
  }
}

async function nativeAnalyze(payload, { signal = null, onEvent = null } = {}) {
  const app = nativeWailsApp()
  if (!app || typeof app.AnalyzeQuestion !== 'function') return null
  const clientRequestId = globalThis.crypto?.randomUUID
    ? globalThis.crypto.randomUUID()
    : `analysis-${Date.now()}-${Math.random().toString(16).slice(2)}`
  const request = {
    client_request_id: clientRequestId,
    workspace_id: String(payload?.workspace_id || ''),
    conversation_id: String(payload?.conversation_id || ''),
    parent_turn_id: payload?.selected_parent_turn_id ? String(payload.selected_parent_turn_id) : null,
    question: String(payload?.question || ''),
    current_code: String(payload?.current_code || ''),
    timeout_seconds: 360,
    attachments: Array.isArray(payload?.attachments) ? payload.attachments : [],
  }
  let unsubscribe = () => {}
  if (onEvent && window.runtime?.EventsOnMultiple) {
    unsubscribe = EventsOn('agent-runtime-event', (event) => {
      if (String(event?.client_request_id || '') !== clientRequestId) return
      const type = String(event?.type || 'status')
      const data = event?.data && typeof event.data === 'object' ? { ...event.data } : {}
      if (type === 'agent_status' && !data.message) data.message = nativeStatusMessage(data.stage)
      onEvent({ event: type, data })
    }) || (() => {})
  }
  const onAbort = () => {
    if (typeof app.CancelAgentAnalysis === 'function') {
      void app.CancelAgentAnalysis(request.workspace_id, clientRequestId)
    }
  }
  if (signal) signal.addEventListener('abort', onAbort, { once: true })
  try {
    const raw = await withAbortSignal(app.AnalyzeQuestion(request), signal)
    return normalizeNativeAnalysis(raw)
  } catch (error) {
    if (!signal?.aborted && onEvent) {
      onEvent({
        event: 'error',
        data: { message: extractApiErrorMessage(error, 'The local analysis runtime stopped unexpectedly.') },
      })
    }
    throw error
  } finally {
    if (signal) signal.removeEventListener('abort', onAbort)
    unsubscribe()
  }
}

const resolvedEnvBase = (import.meta.env.VITE_API_BASE || '').trim()
let apiBaseUrl = resolvedEnvBase || getDefaultApiBase()
let authBearerToken = ''
let resolveApiBaseReady = () => {}
const apiBaseReadyPromise = new Promise((resolve) => {
  resolveApiBaseReady = resolve
})

function normalizeApiBase(rawBase) {
  return String(rawBase || '').trim().replace(/\/+$/, '')
}

function setResolvedApiBase(rawBase) {
  const normalized = normalizeApiBase(rawBase)
  if (!normalized) return
  apiBaseUrl = normalized
  axios.defaults.baseURL = normalized
  if (typeof window !== 'undefined') {
    window.__INQUIRA_API_BASE__ = normalized
  }
  resolveApiBaseReady(normalized)
}

function initializeTauriApiBase() {
  if (typeof window === 'undefined') return
  if (resolvedEnvBase) {
    setResolvedApiBase(resolvedEnvBase)
    return
  }
  if (!window.__TAURI_INTERNALS__) {
    setResolvedApiBase(apiBaseUrl)
    return
  }

  invoke('get_backend_url')
    .then((value) => {
      setResolvedApiBase(value)
    })
    .catch(() => {
      setResolvedApiBase(apiBaseUrl)
    })
}
const artifactRowsInFlight = new Map()
const artifactRowsCache = new Map()
const ARTIFACT_ROWS_CACHE_LIMIT = 200

function cloneArtifactRowsPayload(payload) {
  return JSON.parse(JSON.stringify(payload ?? null))
}

function readArtifactRowsCache(requestKey) {
  const cached = artifactRowsCache.get(requestKey)
  if (!cached) return null
  artifactRowsCache.delete(requestKey)
  artifactRowsCache.set(requestKey, cached)
  return cloneArtifactRowsPayload(cached)
}

function writeArtifactRowsCache(requestKey, payload) {
  artifactRowsCache.set(requestKey, cloneArtifactRowsPayload(payload))
  if (artifactRowsCache.size <= ARTIFACT_ROWS_CACHE_LIMIT) return
  const oldestKey = artifactRowsCache.keys().next().value
  if (oldestKey) {
    artifactRowsCache.delete(oldestKey)
  }
}

function createAbortError(message = 'Request aborted') {
  const error = new Error(message)
  error.name = 'AbortError'
  return error
}

function isSseTransportError(error) {
  if (!error) return false
  const name = String(error?.name || '').toLowerCase()
  const message = String(error?.message || '').toLowerCase()
  if (name === 'aborterror') return false
  return (
    message.includes('stream ended without final analysis payload') ||
    message.includes('network error') ||
    message.includes('failed to fetch') ||
    message.includes('incomplete_chunked_encoding') ||
    name === 'typeerror'
  )
}

function withAbortSignal(promise, signal) {
  if (!signal) return promise
  if (signal.aborted) return Promise.reject(createAbortError())

  return new Promise((resolve, reject) => {
    const onAbort = () => {
      cleanup()
      reject(createAbortError())
    }
    const cleanup = () => {
      signal.removeEventListener('abort', onAbort)
    }
    signal.addEventListener('abort', onAbort, { once: true })
    promise
      .then((value) => {
        cleanup()
        resolve(value)
      })
      .catch((error) => {
        cleanup()
        reject(error)
      })
  })
}

async function authorizedFetch(input, init = {}) {
  const headers = new Headers(init?.headers || {})
  if (authBearerToken && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${authBearerToken}`)
  }
  return fetch(input, {
    ...init,
    headers,
    credentials: init?.credentials || 'include',
  })
}

export function setAuthToken(token) {
  authBearerToken = String(token || '').trim()
}

export function getAuthToken() {
  return authBearerToken
}

// Configure GLOBAL axios defaults
axios.defaults.baseURL = apiBaseUrl
axios.defaults.timeout = 360000 // 6 minutes
axios.defaults.withCredentials = true
axios.defaults.headers.common['Content-Type'] = 'application/json'
initializeTauriApiBase()

async function waitForApiBaseReady(timeoutMs = 5000) {
  if (window?.__INQUIRA_API_BASE__) {
    return window.__INQUIRA_API_BASE__
  }

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('API base resolution timed out.'))
    }, timeoutMs)

    apiBaseReadyPromise
      .then((value) => {
        clearTimeout(timer)
        resolve(value)
      })
      .catch((error) => {
        clearTimeout(timer)
        reject(error)
      })
  })
}

// Request interceptor
axios.interceptors.request.use(
  async (config) => {
    if (authBearerToken) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${authBearerToken}`
    }
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
    const detailText = String(error?.response?.data?.detail || '')
    const isAuthProbe = url.includes('/api/v1/auth/me')
    const isExpectedAuthCheckFailure =
      (status === 401 || !status) &&
      (isAuthProbe || url.includes('/api/v1/auth/logout'))
    const isWorkspaceRuntimePending409 =
      status === 409 &&
      url.includes('/api/v1/workspaces/') &&
      (
        url.includes('/columns') ||
        url.includes('/artifacts') ||
        url.includes('/commands')
      ) &&
      detailText.toLowerCase().includes('workspace runtime')

    if (!isExpectedAuthCheckFailure && !isWorkspaceRuntimePending409) {
      console.error('API Error:', error)
    } else if (isWorkspaceRuntimePending409) {
      console.debug('Runtime pending while workspace starts:', url, detailText)
    }

    // Add more specific error information
    if (error.response) {
      // Server responded with error status
      error.status = error.response.status
      error.statusText = error.response.statusText
      error.data = error.response.data
      error.message = extractApiErrorMessage(
        error,
        error.message || `Request failed with status ${error.response.status}`,
      )
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
  setAuthToken,
  getAuthToken,
  waitForApiBaseReady,
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
        return {
          user_id: 'local-user',
          username: 'Local User',
          email: '',
          plan: 'FREE',
          is_authenticated: false,
          is_guest: true,
          auth_provider: 'local',
          manage_account_url: '',
        }
      }

      throw error
    }
  },

  // Settings management
  async getSettings() {
    const appStore = useAppStore()
    const hasWorkspace = !!appStore.hasWorkspace
    return {
      api_key: null,
      api_key_present: !!appStore.apiKeyConfigured,
      data_path: hasWorkspace ? (appStore.dataFilePath || null) : null,
      context: appStore.schemaContext || '',
      table_name: hasWorkspace ? (appStore.ingestedTableName || null) : null
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

  async setContext(context) {
    const appStore = useAppStore()
    appStore.setSchemaContext(context || '')
    return { detail: 'Context saved.' }
  },

  async setApiKeySettings(apiKeyOrPayload, provider = 'openrouter') {
    const appStore = useAppStore()
    const payload = apiKeyOrPayload && typeof apiKeyOrPayload === 'object' && !Array.isArray(apiKeyOrPayload)
      ? apiKeyOrPayload
      : {
          api_key: apiKeyOrPayload || '',
          provider,
        }
    const response = await this.v1SetApiKey(payload, provider)
    const selectedProvider = String(response?.llm_provider || payload?.provider || provider || 'openrouter').trim().toLowerCase()
    const providerPresence = Boolean(response?.api_key_present_by_provider?.[selectedProvider])
    const fallbackPresence = Boolean(response?.selected_provider_api_key_present ?? response?.api_key_present)
    appStore.setApiKeyConfigured(providerPresence || fallbackPresence || selectedProvider === 'ollama')
    return response || { detail: 'Provider configuration saved.' }
  },

  // Generate schema with context
  async generateSchema(filepath, context = null, forceRegenerate = false) {
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
    const appStore = useAppStore()
    const workspaceId = appStore.activeWorkspaceId
    const tableName = (appStore.ingestedTableName || inferTableNameFromDataPath(filepath || appStore.dataFilePath || '')).trim()
    if (!workspaceId || !tableName) {
      throw new Error('Select a workspace dataset before saving schema.')
    }
    return this.v1SaveDatasetSchema(workspaceId, tableName, { context, columns })
  },

  // Get database and schema paths
  async getDatabasePaths() {
    const appStore = useAppStore()
    if (!appStore.activeWorkspaceId || !appStore.hasWorkspace) {
      return { database_path: null, schema_path: null, base_directory: null }
    }
    const paths = await this.v1GetWorkspacePaths(appStore.activeWorkspaceId)
    return {
      database_path: paths?.duckdb_path || null,
      schema_path: paths?.workspace_dir || null,
      base_directory: paths?.workspace_dir || null,
      terminal_enabled: Boolean(paths?.terminal_enabled),
    }
  },

  async getWorkspaceColumns(workspaceId = null) {
    const appStore = useAppStore()
    const targetWorkspaceId = String(workspaceId || appStore.activeWorkspaceId || '').trim()
    if (!targetWorkspaceId) {
      return { columns: [] }
    }
    const runtimeReady = await appStore.ensureWorkspaceRuntimeReady(targetWorkspaceId)
    if (!runtimeReady) {
      return { columns: [] }
    }
    return this.v1GetWorkspaceColumns(targetWorkspaceId)
  },

  // Code execution (server-side)
  async executeCode(code, timeout = 60, workspaceId = null, options = {}) {
    const appStore = useAppStore()
    const activeWorkspaceId = workspaceId || appStore.activeWorkspaceId
    if (!activeWorkspaceId) {
      throw new Error('Create/select a workspace before running code.')
    }
    const persistToTurn = options?.persistToTurn !== false
    const resultMode = options?.resultMode === 'jupyter' ? 'jupyter' : 'auto'
    console.debug('🚀 [API] Executing code...', { timeout, persistToTurn, resultMode })
    const app = nativeWailsApp()
    if (app?.RunManualCode) {
      const conversationId = String(appStore.activeConversationId || '')
      const parentTurnId = conversationId ? String(appStore.activeTurnId || '') : ''
      const raw = await app.RunManualCode({
        workspace_id: String(activeWorkspaceId),
        conversation_id: conversationId,
        parent_turn_id: parentTurnId || null,
        code: String(code || ''),
        timeout_seconds: Number(timeout || 60),
      })
      return normalizeNativeManualExecution(raw)
    }
    const response = await authorizedFetch(
      `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${activeWorkspaceId}/execute`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          code,
          timeout,
          result_mode: resultMode,
          ...(persistToTurn ? {
            conversation_id: appStore.activeConversationId || null,
            turn_id: appStore.activeTurnId || null,
          } : {}),
        })
      }
    )
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(detail.detail || `Execution request failed (${response.status})`)
    }
    const payload = await response.json()
    return normalizeExecutionResponse(payload)
  },

  async getDataframeArtifactRows(workspaceId, artifactId, offset = 0, limit = 1000, options = {}) {
    const normalizedSortModel = Array.isArray(options?.sortModel) ? options.sortModel : []
    const normalizedFilterModel = (
      options?.filterModel &&
      typeof options.filterModel === 'object' &&
      !Array.isArray(options.filterModel)
    ) ? options.filterModel : {}
    const normalizedSearchText = String(options?.searchText || '').trim()
    const sortModelPayload = JSON.stringify(normalizedSortModel)
    const filterModelPayload = JSON.stringify(normalizedFilterModel)

    const requestKey = [
      workspaceId,
      artifactId,
      Number(offset || 0),
      Number(limit || 0),
      sortModelPayload,
      filterModelPayload,
      normalizedSearchText,
    ].join(':')
    const cached = readArtifactRowsCache(requestKey)
    if (cached) {
      return withAbortSignal(Promise.resolve(cached), options?.signal || null)
    }
    let inFlight = artifactRowsInFlight.get(requestKey)

    if (!inFlight) {
      inFlight = (async () => {
        const app = nativeWailsApp()
        if (app?.GetWorkspaceArtifactRows) {
          const payload = await app.GetWorkspaceArtifactRows(String(workspaceId || ''), String(artifactId || ''), {
            offset: Number(offset || 0), limit: Number(limit || 0), sort_model: normalizedSortModel,
            filter_model: normalizedFilterModel, search_text: normalizedSearchText,
          })
          writeArtifactRowsCache(requestKey, payload)
          return cloneArtifactRowsPayload(payload)
        }
        const queryParams = new URLSearchParams({
          offset: String(offset),
          limit: String(limit),
        })
        if (sortModelPayload !== '[]') {
          queryParams.set('sort_model', sortModelPayload)
        }
        if (filterModelPayload !== '{}') {
          queryParams.set('filter_model', filterModelPayload)
        }
        if (normalizedSearchText) {
          queryParams.set('search', normalizedSearchText)
        }
        const response = await authorizedFetch(
          `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/artifacts/${artifactId}/rows?${queryParams.toString()}`,
          {
            method: 'GET',
          }
        )
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}))
          throw new Error(detail.detail || `Artifact row fetch failed (${response.status})`)
        }
        const payload = await response.json()
        writeArtifactRowsCache(requestKey, payload)
        return cloneArtifactRowsPayload(payload)
      })().finally(() => {
        artifactRowsInFlight.delete(requestKey)
      })

      artifactRowsInFlight.set(requestKey, inFlight)
    }

    return withAbortSignal(inFlight, options?.signal || null)
  },

  async getTurnDataframeArtifactRows(conversationId, turnId, artifactId, offset = 0, limit = 1000, options = {}) {
    const normalizedSortModel = Array.isArray(options?.sortModel) ? options.sortModel : []
    const normalizedFilterModel = (
      options?.filterModel &&
      typeof options.filterModel === 'object' &&
      !Array.isArray(options.filterModel)
    ) ? options.filterModel : {}
    const normalizedSearchText = String(options?.searchText || '').trim()
    const sortModelPayload = JSON.stringify(normalizedSortModel)
    const filterModelPayload = JSON.stringify(normalizedFilterModel)

    const requestKey = [
      'turn',
      conversationId,
      turnId,
      artifactId,
      Number(offset || 0),
      Number(limit || 0),
      sortModelPayload,
      filterModelPayload,
      normalizedSearchText,
    ].join(':')
    const cached = readArtifactRowsCache(requestKey)
    if (cached) {
      return withAbortSignal(Promise.resolve(cached), options?.signal || null)
    }
    let inFlight = artifactRowsInFlight.get(requestKey)

    if (!inFlight) {
      inFlight = (async () => {
        const app = nativeWailsApp()
        if (app?.GetTurnArtifactRows) {
          const payload = await app.GetTurnArtifactRows(String(conversationId || ''), String(turnId || ''), String(artifactId || ''), {
            offset: Number(offset || 0), limit: Number(limit || 0), sort_model: normalizedSortModel,
            filter_model: normalizedFilterModel, search_text: normalizedSearchText,
          })
          writeArtifactRowsCache(requestKey, payload)
          return cloneArtifactRowsPayload(payload)
        }
        const queryParams = new URLSearchParams({
          offset: String(offset),
          limit: String(limit),
        })
        if (sortModelPayload !== '[]') {
          queryParams.set('sort_model', sortModelPayload)
        }
        if (filterModelPayload !== '{}') {
          queryParams.set('filter_model', filterModelPayload)
        }
        if (normalizedSearchText) {
          queryParams.set('search', normalizedSearchText)
        }
        const response = await authorizedFetch(
          `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/conversations/${conversationId}/turns/${turnId}/artifacts/${artifactId}/rows?${queryParams.toString()}`,
          {
            method: 'GET',
          }
        )
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}))
          throw new Error(detail.detail || `Turn artifact row fetch failed (${response.status})`)
        }
        const payload = await response.json()
        writeArtifactRowsCache(requestKey, payload)
        return cloneArtifactRowsPayload(payload)
      })().finally(() => {
        artifactRowsInFlight.delete(requestKey)
      })

      artifactRowsInFlight.set(requestKey, inFlight)
    }

    return withAbortSignal(inFlight, options?.signal || null)
  },

  async executeTerminalCommand(workspaceId, payload) {
    const response = await authorizedFetch(
      `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/terminal/execute`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload || {}),
      },
    )
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(detail.detail || `Terminal execution failed (${response.status})`)
    }
    return response.json()
  },

  async executeTerminalCommandStream(workspaceId, payload, { signal = null, onEvent = null } = {}) {
    const response = await authorizedFetch(
      `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/terminal/stream`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload || {}),
        signal,
      },
    )
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(detail.detail || `Terminal stream failed (${response.status})`)
    }
    if (!response.body) {
      return this.executeTerminalCommand(workspaceId, payload)
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
        if (evt.event === 'token' && events.length > 1) {
          // Allow UI paint between dense token bursts that arrive in one SSE chunk.
          await new Promise((resolve) => setTimeout(resolve, 0))
        }
        if (evt.event === 'final') {
          finalPayload = evt.data
        } else if (evt.event === 'error') {
          const detail = evt.data?.detail || 'Terminal execution failed.'
          throw new Error(detail)
        }
      }
    }

    if (!finalPayload) {
      throw new Error('Terminal stream ended without a final payload.')
    }
    return finalPayload
  },

  async resetTerminalSession(workspaceId) {
    const response = await authorizedFetch(
      `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/terminal/session/reset`,
      {
        method: 'POST',
      },
    )
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      throw new Error(detail.detail || `Terminal reset failed (${response.status})`)
    }
    return response.json()
  },

  // File data loading — inspect file for columns, then trigger background DuckDB conversion
  async uploadDataPath(filePath) {
    const appStore = useAppStore()
    if (!appStore.activeWorkspaceId) {
      throw new Error('Create/select a workspace before loading a dataset.')
    }

    const workspaceId = appStore.activeWorkspaceId
    const runtimeReady = await appStore.ensureWorkspaceRuntimeReady(workspaceId)
    if (!runtimeReady) {
      const reason = String(appStore.runtimeError || 'Workspace runtime bootstrap failed.')
      throw new Error(reason)
    }
    let ds = null
    try {
      ds = await this.v1AddDataset(workspaceId, filePath)
    } catch (error) {
      const detail = extractApiErrorMessage(error, '')
      const normalizedDetail = String(detail || '').toLowerCase()
      const isWorkspaceLockConflict =
        error?.status === 409 &&
        normalizedDetail.includes('workspace database is currently locked')

      if (!isWorkspaceLockConflict) {
        throw error
      }

      await this.v1ResetWorkspaceRuntime(workspaceId)
      ds = await this.v1AddDataset(workspaceId, filePath)
    }
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

  async getHistory() {
    return client.getChatHistoryHistoryGet()
  },

  // test gemini api
  async testGeminiApi(apiKey, model = '', provider = 'openrouter') {
    const payload = { api_key: apiKey, model: model || undefined, provider }
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

  // V1 Workspace APIs
  async v1ListWorkspaces() {
    const app = nativeWailsApp()
    if (app?.ListWorkspaces) return app.ListWorkspaces()
    return v1Api.workspaces.list()
  },

  async v1CreateWorkspace(name, schemaContext = '') {
    const app = nativeWailsApp()
    if (app?.CreateWorkspace) return app.CreateWorkspace({ name: String(name || ''), schema_context: String(schemaContext || '') })
    return v1Api.workspaces.create(name, schemaContext)
  },

  async v1ActivateWorkspace(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ActivateWorkspace) return app.ActivateWorkspace(String(workspaceId || ''))
    return v1Api.workspaces.activate(workspaceId)
  },

  async v1GetWorkspaceSummary(workspaceId) {
    const app = nativeWailsApp()
    if (app?.GetWorkspaceSummary) return app.GetWorkspaceSummary(String(workspaceId || ''))
    return v1Api.workspaces.summary(workspaceId)
  },

  async v1GetWorkspaceAIConfig(workspaceId) {
    const app = nativeWailsApp()
    if (app?.GetWorkspaceAIConfig) return app.GetWorkspaceAIConfig(String(workspaceId || ''))
    return v1Api.workspaces.aiConfig(workspaceId)
  },

  async v1UpdateWorkspaceAIConfig(workspaceId, payload) {
    const app = nativeWailsApp()
    if (app?.UpdateWorkspaceAIConfig) return app.UpdateWorkspaceAIConfig(String(workspaceId || ''), payload)
    return v1Api.workspaces.updateAiConfig(workspaceId, payload)
  },

  async v1ResetWorkspaceAIConfig(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ResetWorkspaceAIConfig) return app.ResetWorkspaceAIConfig(String(workspaceId || ''))
    return v1Api.workspaces.resetAiConfig(workspaceId)
  },

  async v1RenameWorkspace(workspaceId, name, schemaContext = undefined) {
    const app = nativeWailsApp()
    if (app?.UpdateWorkspace) {
      let resolvedName = String(name || '').trim()
      if (!resolvedName && app.GetWorkspaceSummary) {
        const summary = await app.GetWorkspaceSummary(String(workspaceId || ''))
        resolvedName = String(summary?.name || '').trim()
      }
      return app.UpdateWorkspace({
        workspace_id: String(workspaceId || ''),
        name: resolvedName,
        ...(schemaContext === undefined ? {} : { schema_context: String(schemaContext || '') }),
      })
    }
    return v1Api.workspaces.rename(workspaceId, name, schemaContext)
  },

  async v1ClearWorkspaceDatabase(workspaceId) {
    return v1Api.workspaces.clearDatabase(workspaceId)
  },

  async v1DeleteWorkspace(workspaceId) {
    const app = nativeWailsApp()
    if (app?.DeleteWorkspace) return app.DeleteWorkspace(String(workspaceId || ''))
    return v1Api.workspaces.remove(workspaceId)
  },

  async v1ListWorkspaceDeletionJobs() {
    return v1Api.workspaces.deletions()
  },

  async v1GetWorkspaceDeletionJob(jobId) {
    return v1Api.workspaces.deletionById(jobId)
  },

  async v1ListDatasets(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ListWorkspaceDatasets) return app.ListWorkspaceDatasets(String(workspaceId || ''))
    return v1Api.datasets.list(workspaceId)
  },

  async v1GetPreferences(provider = null) {
    const app = nativeWailsApp()
    if (app?.GetModelPreferences) return app.GetModelPreferences(String(provider || ''))
    return v1Api.preferences.get(provider)
  },

  async v1UpdatePreferences(payload) {
    const app = nativeWailsApp()
    if (app?.UpdateModelPreferences) return app.UpdateModelPreferences(payload || {})
    return v1Api.preferences.update(payload)
  },

  async v1RefreshProviderModels(payload) {
    const app = nativeWailsApp()
    if (app?.RefreshProviderModels) return app.RefreshProviderModels(payload || {})
    return v1Api.preferences.refreshModels(payload)
  },

  async v1SearchProviderModels(provider, query, limit = 25) {
    const app = nativeWailsApp()
    if (app?.SearchProviderModels) {
      return app.SearchProviderModels(
        String(provider || ''),
        String(query || ''),
        Number(limit || 25),
      )
    }
    return v1Api.preferences.searchModels({
      provider,
      query,
      limit,
    })
  },

  async v1VerifyApiKey(provider, apiKey) {
    const app = nativeWailsApp()
    if (app?.VerifyProviderAPIKey) {
      return app.VerifyProviderAPIKey(String(provider || ''), String(apiKey || ''))
    }
    return v1Api.preferences.verifyKey(provider, apiKey)
  },

  async v1SetApiKey(apiKeyOrPayload, provider = 'openrouter') {
    const payload = apiKeyOrPayload && typeof apiKeyOrPayload === 'object' && !Array.isArray(apiKeyOrPayload)
      ? apiKeyOrPayload
      : { api_key: apiKeyOrPayload, provider }
    const app = nativeWailsApp()
    if (app?.SaveProviderConfiguration) return app.SaveProviderConfiguration(payload)
    return v1Api.preferences.setApiKey(payload)
  },

  async v1DeleteApiKey(provider = 'openrouter') {
    const app = nativeWailsApp()
    if (app?.DeleteProviderAPIKey) return app.DeleteProviderAPIKey(String(provider || 'openrouter'))
    return v1Api.preferences.deleteApiKey(provider)
  },

  async v1GetTermsAndConditions() {
    return axios.get('/api/v1/legal/terms')
  },

  async v1GetWorkspacePaths(workspaceId) {
    const app = nativeWailsApp()
    if (app?.GetWorkspacePaths) return app.GetWorkspacePaths(String(workspaceId || ''))
    return axios.get(`/api/v1/workspaces/${workspaceId}/paths`)
  },

  async v1AddDataset(workspaceId, sourcePath, tableName = '') {
    const app = nativeWailsApp()
    if (app?.SelectWorkspaceDataset) return app.SelectWorkspaceDataset(String(workspaceId || ''), String(sourcePath || ''), String(tableName || ''))
    return v1Api.datasets.add(workspaceId, sourcePath)
  },

  async v1AddDatasetsBatch(workspaceId, sourcePaths) {
    return v1Api.datasets.addBatch(workspaceId, sourcePaths)
  },

  async v1ListDatasetIngestionJobs(workspaceId) {
    return v1Api.datasets.ingestions(workspaceId)
  },

  async v1ResumeDatasetIngestionJobs(workspaceId) {
    return v1Api.datasets.resumeIngestions(workspaceId)
  },

  async v1GetDatasetIngestionJob(workspaceId, jobId) {
    return v1Api.datasets.ingestionById(workspaceId, jobId)
  },

  async v1DeleteDataset(workspaceId, tableName) {
    return v1Api.datasets.remove(workspaceId, tableName)
  },

  async v1ListDatasetDeletionJobs(workspaceId) {
    return v1Api.datasets.deletions(workspaceId)
  },

  async v1GetDatasetDeletionJob(workspaceId, jobId) {
    return v1Api.datasets.deletionById(workspaceId, jobId)
  },

  async v1GetDatasetSchema(workspaceId, tableName) {
    const app = nativeWailsApp()
    if (app?.GetWorkspaceDatasetSchema) return app.GetWorkspaceDatasetSchema(String(workspaceId || ''), String(tableName || ''))
    return axios.get(`/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema`)
  },

  async v1SaveDatasetSchema(workspaceId, tableName, payload) {
    const app = nativeWailsApp()
    if (app?.SaveWorkspaceDatasetSchema) {
      return app.SaveWorkspaceDatasetSchema({
        workspace_id: String(workspaceId || ''),
        table_name: String(tableName || ''),
        ...(Object.prototype.hasOwnProperty.call(payload || {}, 'context') ? { context: String(payload?.context || '') } : {}),
        columns: Array.isArray(payload?.columns) ? payload.columns : [],
      })
    }
    return axios.post(`/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema`, payload)
  },

  async v1RegenerateDatasetSchema(workspaceId, tableName, payload = {}) {
    const app = nativeWailsApp()
    if (app?.RegenerateWorkspaceDatasetSchema) {
      return app.RegenerateWorkspaceDatasetSchema({
        workspace_id: String(workspaceId || ''),
        table_name: String(tableName || ''),
        ...(Object.prototype.hasOwnProperty.call(payload || {}, 'context') ? { context: String(payload?.context || '') } : {}),
      })
    }
    return axios.post(
      `/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema/regenerate`,
      payload
    )
  },

  async v1EnqueueDatasetSchemaRegeneration(workspaceId, tableName) {
    const app = nativeWailsApp()
    if (app?.RegenerateWorkspaceDatasetSchema) {
      const schema = await app.RegenerateWorkspaceDatasetSchema({
        workspace_id: String(workspaceId || ''),
        table_name: String(tableName || ''),
      })
      return { queued: false, completed: true, schema }
    }
    return v1Api.datasets.enqueueSchemaRegeneration(workspaceId, tableName)
  },

  async v1SyncBrowserDataset(workspaceId, payload) {
    return v1Api.datasets.syncBrowser(workspaceId, payload)
  },

  async v1ListConversations(workspaceId, limit = 50) {
    const app = nativeWailsApp()
    if (app?.ListConversations) {
      const conversations = await app.ListConversations(String(workspaceId || ''))
      return { conversations: (Array.isArray(conversations) ? conversations : []).slice(0, limit) }
    }
    return v1Api.conversations.list(workspaceId, limit)
  },

  async v1CreateConversation(workspaceId, title = null) {
    const app = nativeWailsApp()
    if (app?.CreateConversation) {
      return app.CreateConversation({ workspace_id: String(workspaceId || ''), title: String(title || 'New conversation') })
    }
    return v1Api.conversations.create(workspaceId, title)
  },

  async v1DeleteConversation(conversationId) {
    const app = nativeWailsApp()
    if (app?.DeleteConversation) return app.DeleteConversation(String(conversationId || ''))
    return v1Api.conversations.remove(conversationId)
  },

  async v1UpdateConversation(conversationId, title) {
    const app = nativeWailsApp()
    if (app?.UpdateConversation) return app.UpdateConversation(String(conversationId || ''), String(title || ''))
    return v1Api.conversations.update(conversationId, { title })
  },

  async v1GetConversationUsage(conversationId) {
    if (nativeWailsApp()) {
      return { conversation_id: String(conversationId || ''), request_count: 0, usage: {} }
    }
    return v1Api.conversations.usage(conversationId)
  },

  async v1ListTurns(conversationId, limit = 5, before = null) {
    const app = nativeWailsApp()
    if (app?.ListConversationTurns) {
      const all = (await app.ListConversationTurns(String(conversationId || ''))).map(normalizeNativeTurn).reverse()
      return { turns: all.slice(0, limit), next_cursor: null }
    }
    const params = { limit }
    if (before) params.before = before
    return v1Api.conversations.turns(conversationId, params)
  },

  async v1GetTurn(conversationId, turnId) {
    const app = nativeWailsApp()
    if (app?.GetConversationTurn) return normalizeNativeTurn(await app.GetConversationTurn(String(turnId || '')))
    return axios.get(`/api/v1/conversations/${conversationId}/turns/${turnId}`)
  },

  async v1GetTurnRelations(conversationId, turnId) {
    const app = nativeWailsApp()
    if (app?.ListConversationTurns) {
      const turns = (await app.ListConversationTurns(String(conversationId || ''))).map(normalizeNativeTurn)
      const index = turns.findIndex((turn) => String(turn.id) === String(turnId))
      const current = index >= 0 ? turns[index] : null
      return {
        current,
        parent: current?.parent_turn_id ? turns.find((turn) => String(turn.id) === String(current.parent_turn_id)) || null : null,
        children: current ? turns.filter((turn) => String(turn.parent_turn_id || '') === String(current.id)) : [],
        previous_turn: index > 0 ? turns[index - 1] : null,
        next_turn: index >= 0 && index < turns.length - 1 ? turns[index + 1] : null,
      }
    }
    return axios.get(`/api/v1/conversations/${conversationId}/turns/${turnId}/relations`)
  },

  async v1GetTurnTree(conversationId, currentTurnId = null) {
    const app = nativeWailsApp()
    if (app?.ListConversationTurns) {
      const tree = nativeTurnTree(await app.ListConversationTurns(String(conversationId || '')))
      return { conversation_id: String(conversationId || ''), current_turn_id: currentTurnId, roots: tree.roots }
    }
    const params = {}
    if (currentTurnId) params.current_turn_id = currentTurnId
    return axios.get(`/api/v1/conversations/${conversationId}/turn-tree`, { params })
  },

  async v1GetWorkspaceTurnTree(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ListConversations && app?.ListConversationTurns) {
      const conversations = await app.ListConversations(String(workspaceId || ''))
      return {
        workspace_id: String(workspaceId || ''),
        conversations: await Promise.all((Array.isArray(conversations) ? conversations : []).map(async (item) => {
          const tree = nativeTurnTree(await app.ListConversationTurns(String(item.id || '')))
          return { ...item, roots: tree.roots, final_turn_id: item.final_turn_id || null, usage_summary: null }
        })),
      }
    }
    return axios.get(`/api/v1/workspaces/${workspaceId}/turn-tree`)
  },

  async v1DeleteTurn(conversationId, turnId) {
    const app = nativeWailsApp()
    if (app?.DeleteConversationTurn) return app.DeleteConversationTurn(String(conversationId || ''), String(turnId || ''))
    return axios.delete(`/api/v1/conversations/${conversationId}/turns/${turnId}`)
  },

  async v1MoveTurn(conversationId, turnId, parentTurnId) {
    const app = nativeWailsApp()
    if (app?.MoveConversationTurn) return app.MoveConversationTurn({ conversation_id: String(conversationId || ''), turn_id: String(turnId || ''), parent_turn_id: parentTurnId ? String(parentTurnId) : null })
    return axios.patch(`/api/v1/conversations/${conversationId}/turns/${turnId}/parent`, {
      parent_turn_id: parentTurnId,
    })
  },

  async v1ReorderTurns(conversationId, parentTurnId, turnIds) {
    const app = nativeWailsApp()
    if (app?.ReorderConversationTurns) return app.ReorderConversationTurns({ conversation_id: String(conversationId || ''), parent_turn_id: parentTurnId ? String(parentTurnId) : null, turn_ids: Array.isArray(turnIds) ? turnIds.map(String) : [] })
    return axios.patch(`/api/v1/conversations/${conversationId}/turns/order`, {
      parent_turn_id: parentTurnId || null,
      turn_ids: Array.isArray(turnIds) ? turnIds : [],
    })
  },

  async v1GetFinalTurn(conversationId) {
    const app = nativeWailsApp()
    if (app?.GetFinalConversationTurn) return normalizeNativeTurn(await app.GetFinalConversationTurn(String(conversationId || '')))
    if (app?.ListConversationTurns) {
      const turns = (await app.ListConversationTurns(String(conversationId || ''))).map(normalizeNativeTurn)
      return [...turns].reverse().find((turn) => turn.status === 'completed') || null
    }
    return axios.get(`/api/v1/conversations/${conversationId}/final-turn`)
  },

  async v1MarkFinalTurn(conversationId, turnId) {
    const app = nativeWailsApp()
    if (app?.MarkFinalConversationTurn) return normalizeNativeTurn(await app.MarkFinalConversationTurn(String(conversationId || ''), String(turnId || '')))
    return axios.post(`/api/v1/conversations/${conversationId}/turns/${turnId}/final`)
  },

  async v1RerunFinalTurn(conversationId) {
    const app = nativeWailsApp()
    if (app?.RerunFinalConversationTurn) return normalizeNativeAnalysis(await app.RerunFinalConversationTurn(String(conversationId || '')))
    return axios.post(`/api/v1/conversations/${conversationId}/final-turn/rerun`)
  },

  async v1Analyze(payload) {
    const native = await nativeAnalyze(payload)
    if (native) return native
    return v1Api.chat.analyze(payload)
  },

  async v1RespondChatIntervention(interventionId, selected = []) {
    const app = nativeWailsApp()
    if (app?.RespondAgentIntervention) {
      return app.RespondAgentIntervention(String(interventionId || ''), Array.isArray(selected) ? selected : [])
    }
    return v1Api.chat.respondIntervention(interventionId, {
      selected: Array.isArray(selected) ? selected : [],
    })
  },

  async v1InstallRunnerPackage(payload) {
    return v1Api.runtime.installRunnerPackage(payload)
  },

  async v1GetWorkspaceColumns(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ListWorkspaceColumns) return app.ListWorkspaceColumns(String(workspaceId || ''))
    return v1Api.runtime.workspaceColumns(workspaceId)
  },

  async v1ListWorkspaceCommands(workspaceId) {
    return v1Api.runtime.listWorkspaceCommands(workspaceId)
  },

  async v1ExecuteWorkspaceCommand(workspaceId, payload) {
    return v1Api.runtime.executeWorkspaceCommand(workspaceId, payload)
  },

  async v1BootstrapWorkspaceRuntime(workspaceId) {
    const app = nativeWailsApp()
    if (app?.PrepareWorkspaceCatalog) {
      await app.PrepareWorkspaceCatalog(String(workspaceId || ''))
      return { reset: true, status: 'ready' }
    }
    return v1Api.runtime.bootstrapWorkspaceRuntime(workspaceId)
  },

  async v1RetryWorkspaceRuntime(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ResetWorkspaceKernel && app?.PrepareWorkspaceCatalog) {
      await app.ResetWorkspaceKernel(String(workspaceId || ''))
      await app.PrepareWorkspaceCatalog(String(workspaceId || ''))
      return { reset: true, status: 'ready' }
    }
    return v1Api.runtime.retryWorkspaceRuntime(workspaceId)
  },

  async v1HardResetWorkspaceRuntime(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ResetWorkspaceKernel && app?.PrepareWorkspaceCatalog) {
      await app.ResetWorkspaceKernel(String(workspaceId || ''))
      await app.PrepareWorkspaceCatalog(String(workspaceId || ''))
      return { reset: true, status: 'ready' }
    }
    return v1Api.runtime.hardResetWorkspaceRuntime(workspaceId)
  },

  async v1GetWorkspaceResourceRecommendation() {
    const app = nativeWailsApp()
    if (app?.RuntimeStatus) return { enabled: false, candidates: [] }
    return v1Api.runtime.workspaceResourceRecommendation()
  },

  async v1GetWorkspaceRuntimeStatus(workspaceId) {
    const app = nativeWailsApp()
    if (app?.RuntimeStatus && app?.GetWorkspaceKernelStatus) {
      const provision = await app.RuntimeStatus()
      if (!provision?.ready && !provision?.Ready) return { status: 'error' }
      const kernel = await app.GetWorkspaceKernelStatus(String(workspaceId || ''))
      const status = String(kernel?.status || '').toLowerCase()
      return { status: ['running', 'busy'].includes(status) ? 'busy' : 'ready' }
    }
    return v1Api.runtime.workspaceRuntimeStatus(workspaceId)
  },

  async v1InterruptWorkspaceRuntime(workspaceId) {
    const app = nativeWailsApp()
    if (app?.InterruptWorkspaceKernel) return { interrupted: await app.InterruptWorkspaceKernel(String(workspaceId || '')) }
    return v1Api.runtime.workspaceRuntimeInterrupt(workspaceId)
  },

  async v1ResetWorkspaceRuntime(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ResetWorkspaceKernel) return { reset: await app.ResetWorkspaceKernel(String(workspaceId || '')) }
    return v1Api.runtime.workspaceRuntimeReset(workspaceId)
  },

  async v1RestartWorkspaceRuntime(workspaceId) {
    const app = nativeWailsApp()
    if (app?.ResetWorkspaceKernel && app?.PrepareWorkspaceCatalog) {
      await app.ResetWorkspaceKernel(String(workspaceId || ''))
      await app.PrepareWorkspaceCatalog(String(workspaceId || ''))
      return { reset: true, status: 'ready' }
    }
    return v1Api.runtime.workspaceRuntimeRestart(workspaceId)
  },

  async v1AnalyzeStream(payload, { signal = null, onEvent = null } = {}) {
    const native = await nativeAnalyze(payload, { signal, onEvent })
    if (native) return native
    const url = `${apiBaseUrl.replace(/\/+$/, '')}${v1Api.chat.stream}`
    const response = await authorizedFetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload),
      signal
    })

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`
      let responsePayload = null
      try {
        const text = await response.text()
        if (text) {
          try {
            responsePayload = JSON.parse(text)
          } catch (_error) {
            responsePayload = { detail: text }
          }
          detail = extractApiErrorMessage(
            { response: { data: responsePayload } },
            detail,
          )
        }
      } catch (_) {
        // keep default
      }
      const err = new Error(detail)
      err.status = response.status
      err.data = responsePayload
      throw err
    }

    if (!response.body) {
      throw new Error('Streaming not supported by browser/runtime.')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finalPayload = null

    try {
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
            const detail = extractApiErrorMessage(
              { response: { data: evt.data } },
              'Streaming analysis failed.',
            )
            const err = new Error(detail)
            err.status = evt.data?.status_code || 500
            err.data = evt.data
            throw err
          }
        }
      }
      if (!finalPayload) {
        throw new Error('Stream ended without final analysis payload.')
      }
      return finalPayload
    } catch (error) {
      if (signal?.aborted || error?.name === 'AbortError' || !isSseTransportError(error)) {
        throw error
      }
      if (onEvent) {
        onEvent({
          event: 'status',
          data: {
            stage: 'stream_recovery',
            message: 'Streaming connection dropped. Retrying without stream.',
          },
        })
      }
      const response = await v1Api.chat.analyze(payload)
      return response?.data || response
    }
  },

  async v1ListWorkspaceArtifacts(workspaceId, kind = 'dataframe', options = {}) {
    const app = nativeWailsApp()
    if (app?.ListWorkspaceArtifacts) return app.ListWorkspaceArtifacts(String(workspaceId || ''), String(kind || ''))
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/artifacts?kind=${encodeURIComponent(kind)}`
    const response = await authorizedFetch(url, {
      method: 'GET',
      signal: options?.signal || null,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Artifact list fetch failed (${response.status})`)
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async v1ListTurnArtifacts(conversationId, turnId, kind = 'dataframe', options = {}) {
    const app = nativeWailsApp()
    if (app?.ListTurnArtifactSummaries) return app.ListTurnArtifactSummaries(String(conversationId || ''), String(turnId || ''), String(kind || ''))
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/conversations/${conversationId}/turns/${turnId}/artifacts?kind=${encodeURIComponent(kind)}`
    const response = await authorizedFetch(url, {
      method: 'GET',
      signal: options?.signal || null,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Turn artifact list fetch failed (${response.status})`)
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async v1GetTurnArtifactMetadata(conversationId, turnId, artifactId, options = {}) {
    const app = nativeWailsApp()
    if (app?.GetTurnArtifactMetadata) return app.GetTurnArtifactMetadata(String(conversationId || ''), String(turnId || ''), String(artifactId || ''))
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/conversations/${conversationId}/turns/${turnId}/artifacts/${artifactId}`
    const response = await authorizedFetch(url, {
      method: 'GET',
      signal: options?.signal || null,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Turn artifact metadata fetch failed (${response.status})`)
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async v1DeleteTurnArtifact(conversationId, turnId, artifactId, options = {}) {
    const app = nativeWailsApp()
    if (app?.DeleteTurnArtifact) return app.DeleteTurnArtifact(String(conversationId || ''), String(turnId || ''), String(artifactId || ''))
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/conversations/${conversationId}/turns/${turnId}/artifacts/${artifactId}`
    const response = await authorizedFetch(url, {
      method: 'DELETE',
      signal: options?.signal || null,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Turn artifact delete failed (${response.status})`)
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async v1GetWorkspaceArtifactUsage(workspaceId, options = {}) {
    const app = nativeWailsApp()
    if (app?.GetWorkspaceArtifactUsage) return app.GetWorkspaceArtifactUsage(String(workspaceId || ''))
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/artifacts/usage`
    const response = await authorizedFetch(url, {
      method: 'GET',
      signal: options?.signal || null,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Artifact usage fetch failed (${response.status})`)
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async v1GetWorkspaceArtifactMetadata(workspaceId, artifactId, options = {}) {
    const app = nativeWailsApp()
    if (app?.GetWorkspaceArtifactMetadata) return app.GetWorkspaceArtifactMetadata(String(workspaceId || ''), String(artifactId || ''))
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/artifacts/${artifactId}`
    const response = await authorizedFetch(url, {
      method: 'GET',
      signal: options?.signal || null,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Artifact metadata fetch failed (${response.status})`)
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async v1DeleteWorkspaceArtifact(workspaceId, artifactId, options = {}) {
    const app = nativeWailsApp()
    if (app?.DeleteWorkspaceArtifact) return app.DeleteWorkspaceArtifact(String(workspaceId || ''), String(artifactId || ''))
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/artifacts/${artifactId}`
    const response = await authorizedFetch(url, {
      method: 'DELETE',
      signal: options?.signal || null,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Artifact delete failed (${response.status})`)
      err.status = response.status
      throw err
    }
    return response.json()
  },

  async v1GetCurrentUser(options = {}) {
    return v1Api.auth.me(options)
  },

  async subscribeWorkspaceArtifactUsage(workspaceId, { signal = null, onEvent = null } = {}) {
    const url = `${apiBaseUrl.replace(/\/+$/, '')}/api/v1/workspaces/${workspaceId}/artifacts/usage/stream`
    const response = await authorizedFetch(url, {
      method: 'GET',
      headers: {
        Accept: 'text/event-stream',
      },
      signal,
    })
    if (!response.ok) {
      const detail = await response.json().catch(() => ({}))
      const err = new Error(detail.detail || `Artifact usage stream failed (${response.status})`)
      err.status = response.status
      throw err
    }
    if (!response.body) {
      throw new Error('Artifact usage stream is not available in this runtime.')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const { events, remainder } = parseSseBuffer(buffer)
      buffer = remainder

      for (const evt of events) {
        if (onEvent) onEvent(evt)
        if (evt.event === 'error') {
          const detail = evt.data?.detail || 'Artifact usage stream failed.'
          const err = new Error(detail)
          err.status = evt.data?.status_code || 500
          throw err
        }
      }
    }
  },

  async v1Logout() {
    return v1Api.auth.logout()
  }
}

export default apiService
