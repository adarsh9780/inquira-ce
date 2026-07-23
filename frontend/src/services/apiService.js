import { EventsOn } from '../../wailsjs/runtime/runtime'
import { useAppStore } from '../stores/appStore'
import { extractApiErrorMessage } from '../utils/apiError'
import { normalizeExecutionResponse } from '../utils/runtimeExecution'

function wailsApp() {
  if (typeof window === 'undefined') return null
  return window.go?.main?.App || null
}

function requireWailsMethod(method) {
  const app = wailsApp()
  if (!app || typeof app[method] !== 'function') {
    throw new Error(`The ${method} desktop bridge is unavailable. Open this feature in the installed app.`)
  }
  return app[method].bind(app)
}

function createAbortError(message = 'Request aborted') {
  const error = new Error(message)
  error.name = 'AbortError'
  return error
}

function withAbortSignal(promise, signal = null) {
  if (!signal) return promise
  if (signal.aborted) return Promise.reject(createAbortError())
  return new Promise((resolve, reject) => {
    const cleanup = () => signal.removeEventListener('abort', onAbort)
    const onAbort = () => {
      cleanup()
      reject(createAbortError())
    }
    signal.addEventListener('abort', onAbort, { once: true })
    Promise.resolve(promise).then(
      (value) => {
        cleanup()
        resolve(value)
      },
      (error) => {
        cleanup()
        reject(error)
      },
    )
  })
}

function normalizeNativeTurn(turn) {
  if (!turn || typeof turn !== 'object') return turn
  const parse = (value, fallback) => {
    if (typeof value !== 'string' || !value.trim()) return fallback
    try {
      return JSON.parse(value)
    } catch (_error) {
      return fallback
    }
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
    usage: turn?.metadata?.token_usage || null,
    children: [],
  }]))
  const roots = []
  for (const turn of normalized) {
    const node = nodes.get(String(turn.id))
    const parent = turn.parent_turn_id ? nodes.get(String(turn.parent_turn_id)) : null
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  const compare = (left, right) => (
    Number(left?.sibling_order || 0) - Number(right?.sibling_order || 0)
    || Number(left?.sequence || 0) - Number(right?.sequence || 0)
  )
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
  const artifacts = (Array.isArray(raw?.artifacts) ? raw.artifacts : []).map((artifact) => ({
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
    execution: { ...execution, run_id: String(raw?.run_id || ''), artifacts },
    result,
    result_kind: execution.result_kind || '',
    artifacts,
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

async function analyze(payload, { signal = null, onEvent = null } = {}) {
  const app = wailsApp()
  const run = requireWailsMethod('AnalyzeQuestion')
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
  if (onEvent && typeof window !== 'undefined' && window.runtime?.EventsOnMultiple) {
    unsubscribe = EventsOn('agent-runtime-event', (event) => {
      if (String(event?.client_request_id || '') !== clientRequestId) return
      const type = String(event?.type || 'status')
      const data = event?.data && typeof event.data === 'object' ? { ...event.data } : {}
      if (type === 'agent_status' && !data.message) data.message = nativeStatusMessage(data.stage)
      onEvent({ event: type, data })
    }) || (() => {})
  }
  const onAbort = () => {
    if (typeof app?.CancelAgentAnalysis === 'function') {
      void app.CancelAgentAnalysis(request.workspace_id, clientRequestId)
    }
  }
  signal?.addEventListener('abort', onAbort, { once: true })
  try {
    return normalizeNativeAnalysis(await withAbortSignal(run(request), signal))
  } catch (error) {
    if (!signal?.aborted && onEvent) {
      onEvent({
        event: 'error',
        data: { message: extractApiErrorMessage(error, 'The local analysis runtime stopped unexpectedly.') },
      })
    }
    throw error
  } finally {
    signal?.removeEventListener('abort', onAbort)
    unsubscribe()
  }
}

const artifactRowsInFlight = new Map()
const artifactRowsCache = new Map()
const ARTIFACT_ROWS_CACHE_LIMIT = 200

function cloneRows(payload) {
  return JSON.parse(JSON.stringify(payload ?? null))
}

function readRowsCache(key) {
  const cached = artifactRowsCache.get(key)
  if (!cached) return null
  artifactRowsCache.delete(key)
  artifactRowsCache.set(key, cached)
  return cloneRows(cached)
}

function writeRowsCache(key, payload) {
  artifactRowsCache.set(key, cloneRows(payload))
  if (artifactRowsCache.size <= ARTIFACT_ROWS_CACHE_LIMIT) return
  artifactRowsCache.delete(artifactRowsCache.keys().next().value)
}

async function getArtifactRows(method, prefix, args, offset, limit, options = {}) {
  const sortModel = Array.isArray(options?.sortModel) ? options.sortModel : []
  const filterModel = options?.filterModel && typeof options.filterModel === 'object' && !Array.isArray(options.filterModel)
    ? options.filterModel
    : {}
  const searchText = String(options?.searchText || '').trim()
  const key = [
    prefix,
    ...args,
    Number(offset || 0),
    Number(limit || 0),
    JSON.stringify(sortModel),
    JSON.stringify(filterModel),
    searchText,
  ].join(':')
  const cached = readRowsCache(key)
  if (cached) return withAbortSignal(Promise.resolve(cached), options?.signal)
  let inFlight = artifactRowsInFlight.get(key)
  if (!inFlight) {
    inFlight = Promise.resolve(requireWailsMethod(method)(
      ...args.map((value) => String(value || '')),
      {
        offset: Number(offset || 0),
        limit: Number(limit || 0),
        sort_model: sortModel,
        filter_model: filterModel,
        search_text: searchText,
      },
    )).then((payload) => {
      writeRowsCache(key, payload)
      return cloneRows(payload)
    }).finally(() => artifactRowsInFlight.delete(key))
    artifactRowsInFlight.set(key, inFlight)
  }
  return withAbortSignal(inFlight, options?.signal)
}

export const apiService = {
  async executeCode(code, timeout = 60, workspaceId = null) {
    const appStore = useAppStore()
    const target = String(workspaceId || appStore.activeWorkspaceId || '').trim()
    if (!target) throw new Error('Create or select a workspace before running code.')
    const conversationId = String(appStore.activeConversationId || '')
    const parentTurnId = conversationId ? String(appStore.activeTurnId || '') : ''
    const raw = await requireWailsMethod('RunManualCode')({
      workspace_id: target,
      conversation_id: conversationId,
      parent_turn_id: parentTurnId || null,
      code: String(code || ''),
      timeout_seconds: Number(timeout || 60),
    })
    return normalizeNativeManualExecution(raw)
  },

  getDataframeArtifactRows(workspaceId, artifactId, offset = 0, limit = 1000, options = {}) {
    return getArtifactRows(
      'GetWorkspaceArtifactRows',
      'workspace',
      [workspaceId, artifactId],
      offset,
      limit,
      options,
    )
  },

  getTurnDataframeArtifactRows(conversationId, turnId, artifactId, offset = 0, limit = 1000, options = {}) {
    return getArtifactRows(
      'GetTurnArtifactRows',
      'turn',
      [conversationId, turnId, artifactId],
      offset,
      limit,
      options,
    )
  },

  v1GetWorkspaceSummary(workspaceId) {
    return requireWailsMethod('GetWorkspaceSummary')(String(workspaceId || ''))
  },

  v1GetWorkspaceAIConfig(workspaceId) {
    return requireWailsMethod('GetWorkspaceAIConfig')(String(workspaceId || ''))
  },

  v1UpdateWorkspaceAIConfig(workspaceId, payload) {
    return requireWailsMethod('UpdateWorkspaceAIConfig')(String(workspaceId || ''), payload || {})
  },

  async v1RenameWorkspace(workspaceId, name, schemaContext = undefined) {
    let resolvedName = String(name || '').trim()
    const app = wailsApp()
    if (!resolvedName && app?.GetWorkspaceSummary) {
      const summary = await app.GetWorkspaceSummary(String(workspaceId || ''))
      resolvedName = String(summary?.name || '').trim()
    }
    return requireWailsMethod('UpdateWorkspace')({
      workspace_id: String(workspaceId || ''),
      name: resolvedName,
      ...(schemaContext === undefined ? {} : { schema_context: String(schemaContext || '') }),
    })
  },

  v1ListDatasets(workspaceId) {
    return requireWailsMethod('ListWorkspaceDatasets')(String(workspaceId || ''))
  },

  v1GetPreferences(provider = null) {
    return requireWailsMethod('GetModelPreferences')(String(provider || ''))
  },

  v1UpdatePreferences(payload) {
    return requireWailsMethod('UpdateModelPreferences')(payload || {})
  },

  v1SearchProviderModels(provider, query, limit = 25) {
    return requireWailsMethod('SearchProviderModels')(
      String(provider || ''),
      String(query || ''),
      Number(limit || 25),
    )
  },

  v1GetTermsAndConditions() {
    return requireWailsMethod('GetTermsAndConditions')()
  },

  v1GetDatasetSchema(workspaceId, tableName) {
    return requireWailsMethod('GetWorkspaceDatasetSchema')(
      String(workspaceId || ''),
      String(tableName || ''),
    )
  },

  v1SaveDatasetSchema(workspaceId, tableName, payload = {}) {
    return requireWailsMethod('SaveWorkspaceDatasetSchema')({
      workspace_id: String(workspaceId || ''),
      table_name: String(tableName || ''),
      ...(Object.prototype.hasOwnProperty.call(payload, 'context')
        ? { context: String(payload.context || '') }
        : {}),
      columns: Array.isArray(payload.columns) ? payload.columns : [],
    })
  },

  v1RegenerateDatasetSchema(workspaceId, tableName, payload = {}) {
    return requireWailsMethod('RegenerateWorkspaceDatasetSchema')({
      workspace_id: String(workspaceId || ''),
      table_name: String(tableName || ''),
      context: String(payload?.context || ''),
      allow_sample_values: Boolean(payload?.allow_sample_values),
    })
  },

  async v1ListConversations(workspaceId, limit = 50) {
    const response = await requireWailsMethod('ListConversations')(String(workspaceId || ''))
    const conversations = Array.isArray(response) ? response : (response?.conversations || [])
    return { conversations: conversations.slice(0, Number(limit || 50)) }
  },

  v1CreateConversation(workspaceId, title = null) {
    return requireWailsMethod('CreateConversation')({
      workspace_id: String(workspaceId || ''),
      title: String(title || 'New conversation'),
    })
  },

  v1DeleteConversation(conversationId) {
    return requireWailsMethod('DeleteConversation')(String(conversationId || ''))
  },

  v1UpdateConversation(conversationId, title) {
    return requireWailsMethod('UpdateConversation')(
      String(conversationId || ''),
      String(title || ''),
    )
  },

  v1GetConversationUsage(conversationId) {
    return requireWailsMethod('GetConversationUsage')(String(conversationId || ''))
  },

  async v1ListTurns(conversationId, limit = 5) {
    const page = await requireWailsMethod('ListConversationTurnPage')(
      String(conversationId || ''),
      Number(limit || 5),
      '',
    )
    return {
      turns: (Array.isArray(page?.turns) ? page.turns : []).map(normalizeNativeTurn),
    }
  },

  async v1GetTurn(_conversationId, turnId) {
    return normalizeNativeTurn(
      await requireWailsMethod('GetConversationTurn')(String(turnId || '')),
    )
  },

  async v1GetTurnRelations(conversationId, turnId) {
    const turns = (await requireWailsMethod('ListConversationTurns')(String(conversationId || '')))
      .map(normalizeNativeTurn)
    const index = turns.findIndex((turn) => String(turn.id) === String(turnId))
    const current = index >= 0 ? turns[index] : null
    return {
      current,
      parent: current?.parent_turn_id
        ? turns.find((turn) => String(turn.id) === String(current.parent_turn_id)) || null
        : null,
      children: current
        ? turns.filter((turn) => String(turn.parent_turn_id || '') === String(current.id))
        : [],
      previous_turn: index > 0 ? turns[index - 1] : null,
      next_turn: index >= 0 && index < turns.length - 1 ? turns[index + 1] : null,
    }
  },

  async v1GetWorkspaceTurnTree(workspaceId) {
    const app = wailsApp()
    const response = await requireWailsMethod('ListConversations')(String(workspaceId || ''))
    const conversations = Array.isArray(response) ? response : (response?.conversations || [])
    return {
      workspace_id: String(workspaceId || ''),
      conversations: await Promise.all(conversations.map(async (item) => {
        const tree = nativeTurnTree(await requireWailsMethod('ListConversationTurns')(String(item.id || '')))
        const usageSummary = typeof app?.GetConversationUsage === 'function'
          ? await app.GetConversationUsage(String(item.id || ''))
          : null
        return {
          ...item,
          roots: tree.roots,
          final_turn_id: item.final_turn_id || null,
          usage_summary: usageSummary,
        }
      })),
    }
  },

  v1DeleteTurn(conversationId, turnId) {
    return requireWailsMethod('DeleteConversationTurn')(
      String(conversationId || ''),
      String(turnId || ''),
    )
  },

  async v1GetFinalTurn(conversationId) {
    const result = await requireWailsMethod('GetFinalConversationTurn')(String(conversationId || ''))
    return result ? normalizeNativeTurn(result) : null
  },

  async v1MarkFinalTurn(conversationId, turnId) {
    return normalizeNativeTurn(await requireWailsMethod('MarkFinalConversationTurn')(
      String(conversationId || ''),
      String(turnId || ''),
    ))
  },

  v1AnalyzeStream(payload, options = {}) {
    return analyze(payload, options)
  },

  v1ExecuteWorkspaceCommand(workspaceId, payload = {}) {
    return requireWailsMethod('ExecuteWorkspaceCommand')({
      workspace_id: String(workspaceId || ''),
      conversation_id: String(payload.conversation_id || ''),
      text: String(payload.text || ''),
      name: String(payload.name || ''),
      raw_args: String(payload.raw_args || ''),
      default_table: String(payload.default_table || ''),
      row_limit: Number(payload.row_limit || 500),
    })
  },

  async v1GetWorkspaceRuntimeStatus(workspaceId) {
    const provision = await requireWailsMethod('RuntimeStatus')()
    if (!provision?.ready && !provision?.Ready) return { status: 'error' }
    const kernel = await requireWailsMethod('GetWorkspaceKernelStatus')(String(workspaceId || ''))
    const status = String(kernel?.status || '').toLowerCase()
    return { status: ['running', 'busy'].includes(status) ? 'busy' : 'ready' }
  },

  v1ListTurnArtifacts(conversationId, turnId, kind = 'dataframe') {
    return requireWailsMethod('ListTurnArtifactSummaries')(
      String(conversationId || ''),
      String(turnId || ''),
      String(kind || ''),
    )
  },

  v1GetTurnArtifactMetadata(conversationId, turnId, artifactId) {
    return requireWailsMethod('GetTurnArtifactMetadata')(
      String(conversationId || ''),
      String(turnId || ''),
      String(artifactId || ''),
    )
  },

  v1DeleteTurnArtifact(conversationId, turnId, artifactId) {
    return requireWailsMethod('DeleteTurnArtifact')(
      String(conversationId || ''),
      String(turnId || ''),
      String(artifactId || ''),
    )
  },

}

export default apiService
