import type { useConversationStore } from '../stores/conversationStore'

const FINAL_STREAM_NODES = new Set([
  'explain_code',
  'noncode_generator',
  'general_purpose',
  'unsafe_rejector',
  'finalize',
  'chat',
  'reject',
])

type ConversationStore = ReturnType<typeof useConversationStore>
type StreamEvent = { event?: string; data?: any }

export function extractLangGraphTokenText(payload: any): string {
  if (!payload) return ''
  if (typeof payload === 'string') return payload
  if (Array.isArray(payload)) {
    for (const item of payload) {
      const nested = extractLangGraphTokenText(item)
      if (nested) return nested
    }
    return ''
  }
  if (typeof payload === 'object') {
    if (typeof payload.text === 'string' && payload.text) return payload.text
    if (typeof payload.content === 'string' && payload.content) return payload.content
    if (Array.isArray(payload.content)) {
      return extractLangGraphTokenText(payload.content)
    }
  }
  return ''
}

export function useChatStream(
  conversations: ConversationStore,
  normalizeError: (error: unknown, fallback: string) => string,
) {
  function applyStreamEvent(event: StreamEvent, messageId: string, conversationId: string) {
    const options = { conversationId }
    if (['messages', 'messages/partial', 'messages-tuple'].includes(String(event.event || ''))) {
      const text = extractLangGraphTokenText(event.data)
      if (text) conversations.appendLastMessageExplanationChunk(text, messageId, options)
      return
    }
    if (event.event === 'updates') return
    if (event.event === 'token' && typeof event.data?.text === 'string') {
      const nodeName = String(event.data?.node || '').trim().toLowerCase()
      if (FINAL_STREAM_NODES.has(nodeName)) {
        conversations.appendLastMessageExplanationChunk(event.data.text, messageId, options)
      } else {
        conversations.appendLastMessagePlanChunk(event.data.text, event.data.node || '', messageId, options)
      }
      return
    }
    if (event.event === 'llm_progress' && event.data?.message) {
      conversations.appendLastMessageTraceEvent({
        type: 'llm_progress',
        stage: event.data?.stage || '',
        message: event.data.message,
        output: '',
      }, messageId, options)
      return
    }
    if (event.event === 'reasoning' && event.data?.message) {
      conversations.appendLastMessageReasoningEvent({
        stage: event.data?.stage || 'intent',
        message: event.data.message,
        route: event.data?.route || '',
      }, messageId, options)
      return
    }
    if (event.event === 'agent_status' && event.data?.message) {
      conversations.appendLastMessageTraceEvent({
        type: 'status',
        node: 'agent_status',
        stage: event.data.step || '',
        message: event.data.message,
        output: event.data?.detail || event.data?.output || '',
      }, messageId, options)
      return
    }
    if (event.event === 'tool_call' && event.data?.call_id) {
      conversations.appendLastMessageToolCall(event.data, messageId, options)
      return
    }
    if (event.event === 'tool_progress' && event.data?.call_id) {
      conversations.appendLastMessageToolProgress(event.data, messageId, options)
      return
    }
    if (event.event === 'tool_result' && event.data?.call_id) {
      conversations.appendLastMessageToolResult(event.data, messageId, options)
      return
    }
    if (event.event === 'error') {
      conversations.updateLastMessageExplanation(
        normalizeError({ data: event.data }, 'Streaming analysis failed.'),
        messageId,
        options,
      )
      return
    }
    if (event.event === 'token_usage' && event.data?.token_usage) {
      conversations.setLiveTokenUsageForCurrentTurn(event.data.token_usage, options)
    }
  }

  return { applyStreamEvent }
}
