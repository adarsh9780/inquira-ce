import { EventsOn } from '../../wailsjs/runtime/runtime.js'
import { extractApiErrorMessage } from '../utils/apiError.js'
import { normalizeExecutionResponse } from '../utils/runtimeExecution.js'
import { invokeNative, nativeApp, withAbortSignal } from './native.ts'

type RecordValue = Record<string, unknown>
type StreamEvent = { event: string; data: RecordValue }
type AnalyzeOptions = {
  signal?: AbortSignal | null
  onEvent?: ((event: StreamEvent) => void) | null
}

function statusMessage(stage: unknown) {
  return ({
    reading_schema: 'Reading the workspace schema…',
    generating: 'Writing analysis code…',
    executing: 'Running analysis code…',
    retrying: 'Correcting the analysis…',
    explaining: 'Explaining the result…',
    completed: 'Analysis complete.',
  } as Record<string, string>)[String(stage || '')] || 'Working on the analysis…'
}

function normalizeAnalysis(rawValue: unknown) {
  const raw = (rawValue || {}) as RecordValue
  const execution = (raw.execution && typeof raw.execution === 'object'
    ? raw.execution
    : {}) as RecordValue
  const artifacts = (Array.isArray(raw.artifacts) ? raw.artifacts : []).map((value) => {
    const artifact = value as RecordValue
    return { ...artifact, artifact_id: String(artifact.artifact_id || artifact.id || '') }
  })
  let result = execution.result ?? null
  if (
    String(execution.result_kind || '').toLowerCase() === 'dataframe'
    && result
    && typeof result === 'object'
    && Array.isArray((result as RecordValue).rows)
  ) {
    const rows = (result as RecordValue).rows as unknown[]
    result = { ...(result as RecordValue), data: rows, row_count: rows.length }
  }
  const conversation = (raw.conversation || {}) as RecordValue
  const turn = (raw.turn || {}) as RecordValue
  return {
    conversation_id: String(conversation.id || ''),
    turn_id: String(turn.id || ''),
    is_safe: execution.success !== false,
    is_relevant: true,
    code: String(raw.code || ''),
    explanation: String(raw.answer || ''),
    result_explanation: String(raw.answer || ''),
    code_explanation: '',
    run_id: String(raw.run_id || ''),
    execution: { ...execution, run_id: String(raw.run_id || ''), artifacts },
    result,
    result_kind: execution.result_kind || '',
    artifacts,
    route: String(raw.route || ''),
    metadata: raw.metadata && typeof raw.metadata === 'object' ? { ...(raw.metadata as RecordValue) } : {},
  }
}

function normalizeManualExecution(rawValue: unknown) {
  const raw = (rawValue || {}) as RecordValue
  const execution = raw.execution && typeof raw.execution === 'object'
    ? { ...(raw.execution as RecordValue) }
    : {}
  execution.artifacts = (Array.isArray(execution.artifacts) ? execution.artifacts : []).map((value) => {
    const artifact = value as RecordValue
    return { ...artifact, artifact_id: String(artifact.artifact_id || artifact.id || '') }
  })
  const result = execution.result as RecordValue | undefined
  if (
    String(execution.result_kind || '').toLowerCase() === 'dataframe'
    && result
    && Array.isArray(result.rows)
  ) {
    execution.result = { ...result, data: result.rows }
  }
  const conversation = (raw.conversation || {}) as RecordValue
  const turn = (raw.turn || {}) as RecordValue
  return {
    ...normalizeExecutionResponse(execution),
    conversation_id: String(conversation.id || ''),
    turn_id: String(turn.id || ''),
  }
}

export const executionApi = {
  async runCode(request: {
    workspaceId: unknown
    conversationId?: unknown
    parentTurnId?: unknown
    code: unknown
    timeout?: number
  }) {
    const raw = await invokeNative('RunManualCode', {
      workspace_id: String(request.workspaceId || ''),
      conversation_id: String(request.conversationId || ''),
      parent_turn_id: request.parentTurnId ? String(request.parentTurnId) : null,
      code: String(request.code || ''),
      timeout_seconds: Number(request.timeout || 60),
    })
    return normalizeManualExecution(raw)
  },
  async analyze(payload: RecordValue, options: AnalyzeOptions = {}) {
    const signal = options.signal || null
    const onEvent = options.onEvent || null
    const app = nativeApp()
    const clientRequestId = globalThis.crypto?.randomUUID
      ? globalThis.crypto.randomUUID()
      : `analysis-${Date.now()}-${Math.random().toString(16).slice(2)}`
    const request = {
      client_request_id: clientRequestId,
      workspace_id: String(payload.workspace_id || ''),
      conversation_id: String(payload.conversation_id || ''),
      parent_turn_id: payload.selected_parent_turn_id ? String(payload.selected_parent_turn_id) : null,
      question: String(payload.question || ''),
      current_code: String(payload.current_code || ''),
      timeout_seconds: 360,
      attachments: Array.isArray(payload.attachments) ? payload.attachments : [],
    }
    let unsubscribe = () => {}
    if (onEvent && typeof window !== 'undefined' && window.runtime?.EventsOnMultiple) {
      unsubscribe = EventsOn('agent-runtime-event', (eventValue: unknown) => {
        const event = (eventValue || {}) as RecordValue
        if (String(event.client_request_id || '') !== clientRequestId) return
        const type = String(event.type || 'status')
        const data = event.data && typeof event.data === 'object'
          ? { ...(event.data as RecordValue) }
          : {}
        if (type === 'agent_status' && !data.message) data.message = statusMessage(data.stage)
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
      return normalizeAnalysis(await withAbortSignal(invokeNative('AnalyzeQuestion', request), signal))
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
  },
  command(workspaceId: unknown, payload: RecordValue = {}) {
    return invokeNative<RecordValue>('ExecuteWorkspaceCommand', {
      workspace_id: String(workspaceId || ''),
      conversation_id: String(payload.conversation_id || ''),
      text: String(payload.text || ''),
      name: String(payload.name || ''),
      raw_args: String(payload.raw_args || ''),
      default_table: String(payload.default_table || ''),
      row_limit: Number(payload.row_limit || 500),
    })
  },
}
