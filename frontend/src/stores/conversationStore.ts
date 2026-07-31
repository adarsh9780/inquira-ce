import { defineStore } from 'pinia'
import { ref } from 'vue'
import { conversationApi } from '../api/conversations'
import { mergeUsageTotals, normalizeUsage } from '../utils/usageFormat'
import type { ConversationSummary } from '../types/conversation'

type RecordValue = Record<string, any>
const MAX_QUESTION_HISTORY = 30

export const useConversationStore = defineStore('conversations', () => {
  const chatHistory = ref<RecordValue[]>([])
  const questionHistory = ref<string[]>([])
  const currentQuestion = ref('')
  const liveTokenUsage = ref<Record<string, unknown> | null>(null)
  const activeConversationUsage = ref<Record<string, unknown> | null>(null)
  const conversationUsageById = ref<Record<string, unknown>>({})
  const conversations = ref<ConversationSummary[]>([])
  const activeConversationId = ref('')
  const conversationStateById = ref<Record<string, unknown>>({})
  const activeTurnId = ref('')
  const activeTurn = ref<Record<string, unknown> | null>(null)
  const activeTurnCode = ref('')
  const activeTurnRelations = ref<Record<string, unknown> | null>(null)
  const workspaceTurnTree = ref<Record<string, unknown> | null>(null)
  const finalTurnId = ref('')
  let conversationListVersion = 0

  function normalizeId(value: unknown = activeConversationId.value) {
    return String(value || '').trim()
  }

  function emptyTrace() {
    return {
      reasoning: [],
      planText: '',
      planNode: '',
      traceEvents: [],
      toolCalls: [],
      toolProgress: [],
      toolResults: [],
      stopped: false,
      stopReason: '',
    }
  }

  function stateFor(conversationId: unknown, create = true): RecordValue | null {
    const id = normalizeId(conversationId)
    if (!id) return null
    const existing = conversationStateById.value[id] as RecordValue | undefined
    if (existing || !create) return existing || null
    const state = {
      chatHistory: [],
      liveTokenUsage: null,
      activeConversationUsage: null,
      activeTurnId: '',
      activeTurn: null,
      activeTurnCode: '',
      activeTurnRelations: null,
      finalTurnId: '',
    }
    conversationStateById.value = { ...conversationStateById.value, [id]: state }
    return state
  }

  function patchConversationState(conversationId: unknown, patch: RecordValue = {}) {
    const id = normalizeId(conversationId)
    if (!id) return
    const current = stateFor(id) || {}
    conversationStateById.value = {
      ...conversationStateById.value,
      [id]: { ...current, ...patch },
    }
  }

  function activeHistory(conversationId: unknown) {
    const id = normalizeId(conversationId)
    if (!id || id === activeConversationId.value) return chatHistory.value as RecordValue[]
    const state = stateFor(id)
    if (!Array.isArray(state?.chatHistory)) state!.chatHistory = []
    return state!.chatHistory as RecordValue[]
  }

  function commitHistory(conversationId: unknown, history: RecordValue[]) {
    const id = normalizeId(conversationId)
    if (!id || id === activeConversationId.value) chatHistory.value = history
    if (id) patchConversationState(id, { chatHistory: history })
  }

  function addChatMessage(question: unknown, explanation: unknown, options: RecordValue = {}) {
    const conversationId = normalizeId(options.conversationId)
    const history = activeHistory(conversationId)
    const message = {
      id: String(options.localMessageId || `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`),
      question: String(question || ''),
      explanation: String(explanation || ''),
      codeExplanation: '',
      analysisMetadata: {},
      codeSnapshot: '',
      turnId: '',
      attachments: Array.isArray(options.attachments) ? options.attachments : [],
      streamTrace: emptyTrace(),
      createdAt: options.createdAt || new Date().toISOString(),
    }
    commitHistory(conversationId, [...history, message])
    return message.id
  }

  function targetMessage(messageId: unknown, options: RecordValue = {}) {
    const conversationId = normalizeId(options.conversationId)
    const history = activeHistory(conversationId)
    const id = String(messageId || '').trim()
    const index = id
      ? history.findIndex((message) => String(message?.id || '') === id)
      : history.length - 1
    return { conversationId, history, index, message: index >= 0 ? history[index] : null }
  }

  function mutateMessage(
    messageId: unknown,
    options: RecordValue,
    mutate: (message: RecordValue) => RecordValue,
  ) {
    const target = targetMessage(messageId, options)
    if (!target.message || target.index < 0) return
    const next = [...target.history]
    next[target.index] = mutate({ ...target.message })
    commitHistory(target.conversationId, next)
  }

  function withTrace(message: RecordValue) {
    return {
      ...emptyTrace(),
      ...(message.streamTrace && typeof message.streamTrace === 'object' ? message.streamTrace : {}),
    }
  }

  function updateLastMessageExplanation(explanation: unknown, messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => ({ ...message, explanation: String(explanation || '') }))
  }

  function appendLastMessageExplanationChunk(text: unknown, messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => ({
      ...message,
      explanation: `${String(message.explanation || '')}${String(text || '')}`,
    }))
  }

  function setLastMessageCodeExplanation(explanation: unknown, messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => ({ ...message, codeExplanation: String(explanation || '') }))
  }

  function setLastMessageAnalysisMetadata(metadata: unknown, messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => ({
      ...message,
      analysisMetadata: metadata && typeof metadata === 'object' ? metadata : {},
    }))
  }

  function appendLastMessagePlanChunk(text: unknown, node = '', messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => {
      const trace = withTrace(message)
      trace.planText = `${String(trace.planText || '')}${String(text || '')}`
      trace.planNode = String(node || trace.planNode || '')
      return { ...message, streamTrace: trace }
    })
  }

  function appendTraceCollection(
    field: string,
    event: unknown,
    messageId: unknown = null,
    options: RecordValue = {},
  ) {
    mutateMessage(messageId, options, (message) => {
      const trace = withTrace(message)
      trace[field] = [...(Array.isArray(trace[field]) ? trace[field] : []), event]
      return { ...message, streamTrace: trace }
    })
  }

  const appendLastMessageReasoningEvent = (event: unknown, messageId: unknown = null, options: RecordValue = {}) =>
    appendTraceCollection('reasoning', event, messageId, options)
  const appendLastMessageTraceEvent = (event: unknown, messageId: unknown = null, options: RecordValue = {}) =>
    appendTraceCollection('traceEvents', event, messageId, options)
  const appendLastMessageToolCall = (event: unknown, messageId: unknown = null, options: RecordValue = {}) =>
    appendTraceCollection('toolCalls', event, messageId, options)
  const appendLastMessageToolProgress = (event: unknown, messageId: unknown = null, options: RecordValue = {}) =>
    appendTraceCollection('toolProgress', event, messageId, options)
  const appendLastMessageToolResult = (event: unknown, messageId: unknown = null, options: RecordValue = {}) =>
    appendTraceCollection('toolResults', event, messageId, options)

  function markLastMessageStreamStopped(reason = 'Response generation stopped.', messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => ({
      ...message,
      streamTrace: { ...withTrace(message), stopped: true, stopReason: String(reason || '') },
    }))
  }

  function setLastMessageCodeSnapshot(code: unknown, messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => ({ ...message, codeSnapshot: String(code || '') }))
  }

  function setLastMessageTurnId(turnId: unknown, messageId: unknown = null, options: RecordValue = {}) {
    mutateMessage(messageId, options, (message) => ({ ...message, turnId: String(turnId || '') }))
  }

  function addQuestionHistoryEntry(question: unknown) {
    const value = String(question || '').trim()
    if (!value) return
    questionHistory.value = [
      value,
      ...questionHistory.value.filter((item) => item !== value),
    ].slice(0, MAX_QUESTION_HISTORY)
  }

  function setLiveTokenUsageForCurrentTurn(usage: unknown, options: RecordValue = {}) {
    const conversationId = normalizeId(options.conversationId)
    const normalized = normalizeUsage(usage) as Record<string, unknown> | null
    if (!conversationId || conversationId === activeConversationId.value) {
      liveTokenUsage.value = normalized
    }
    if (conversationId) patchConversationState(conversationId, { liveTokenUsage: normalized })
  }

  function syncLiveTokenUsageFromChatHistory(options: RecordValue = {}) {
    const history = activeHistory(options.conversationId)
    const usage = history.reduce<Record<string, unknown> | null>((total, message) => {
      const metadata = message?.analysisMetadata || {}
      return mergeUsageTotals(total, metadata?.token_usage || null) as Record<string, unknown> | null
    }, null)
    setLiveTokenUsageForCurrentTurn(usage, options)
    return usage
  }

  async function fetchActiveConversationUsage(conversationId: unknown = activeConversationId.value) {
    const id = normalizeId(conversationId)
    if (!id) return null
    const summary = await conversationApi.usage(id)
    conversationUsageById.value = { ...conversationUsageById.value, [id]: summary }
    if (id === activeConversationId.value) activeConversationUsage.value = summary
    patchConversationState(id, { activeConversationUsage: summary })
    return summary
  }

  function setActiveConversationId(conversationId: unknown) {
    const nextId = normalizeId(conversationId)
    const previousId = activeConversationId.value
    if (previousId) {
      patchConversationState(previousId, {
        chatHistory: chatHistory.value,
        liveTokenUsage: liveTokenUsage.value,
        activeConversationUsage: activeConversationUsage.value,
        activeTurnId: activeTurnId.value,
        activeTurn: activeTurn.value,
        activeTurnCode: activeTurnCode.value,
        activeTurnRelations: activeTurnRelations.value,
        finalTurnId: finalTurnId.value,
      })
    }
    activeConversationId.value = nextId
    const state = stateFor(nextId, false)
    chatHistory.value = Array.isArray(state?.chatHistory) ? state.chatHistory : []
    liveTokenUsage.value = state?.liveTokenUsage || null
    activeConversationUsage.value = state?.activeConversationUsage || conversationUsageById.value[nextId] || null
    activeTurnId.value = String(state?.activeTurnId || '')
    activeTurn.value = state?.activeTurn || null
    activeTurnCode.value = String(state?.activeTurnCode || '')
    activeTurnRelations.value = state?.activeTurnRelations || null
    finalTurnId.value = String(state?.finalTurnId || '')
  }

  async function fetchConversations(workspaceId: unknown) {
    const target = String(workspaceId || '').trim()
    const requestVersion = ++conversationListVersion
    if (!target) {
      conversations.value = []
      return []
    }
    const response = await conversationApi.list(target, 50)
    if (requestVersion !== conversationListVersion) return conversations.value
    conversations.value = (Array.isArray(response?.conversations) ? response.conversations : []) as ConversationSummary[]
    return conversations.value
  }

  async function createConversation(workspaceId: unknown, title: unknown = null) {
    const target = String(workspaceId || '').trim()
    if (!target) throw new Error('Select a workspace before creating a conversation.')
    const conversation = await conversationApi.create(target, title)
    conversations.value = [conversation as unknown as ConversationSummary, ...conversations.value.filter(
      (item: any) => String(item?.id || '') !== String(conversation?.id || ''),
    )]
    setActiveConversationId(conversation?.id)
    return conversation
  }

  async function ensureActiveConversation(workspaceId: unknown, title: unknown = null) {
    if (activeConversationId.value) return activeConversationId.value
    const conversation = await createConversation(workspaceId, title)
    return String(conversation?.id || '')
  }

  async function fetchConversationTurns(options: RecordValue = {}) {
    const id = normalizeId(options.conversationId)
    if (!id) {
      chatHistory.value = []
      return []
    }
    const response = await conversationApi.listTurns(id, 50)
    const turns = Array.isArray(response?.turns) ? response.turns : []
    const messages = turns.map((turn: any) => ({
      id: String(turn.id || ''),
      question: String(turn.user_text || turn.question || ''),
      explanation: String(turn.assistant_text || turn.answer || ''),
      codeExplanation: '',
      analysisMetadata: turn.metadata || {},
      codeSnapshot: String(turn.code || ''),
      turnId: String(turn.id || ''),
      attachments: [],
      streamTrace: { ...emptyTrace(), toolResults: Array.isArray(turn.tool_events) ? turn.tool_events : [] },
      createdAt: turn.created_at || new Date().toISOString(),
    }))
    commitHistory(id, messages)
    if (id === activeConversationId.value && turns.length > 0) {
      const selected = options.preferLatest ? turns[turns.length - 1] : turns[turns.length - 1]
      setActiveTurnPayload(selected)
    }
    return turns
  }

  async function deleteConversationById(conversationId: unknown) {
    const id = normalizeId(conversationId)
    if (!id) return
    const result = await conversationApi.remove(id)
    if (result && typeof result === 'object' && result.deleted === false) {
      throw new Error('The conversation was not deleted.')
    }

    // Any list request started before the deletion is now stale and must not
    // restore the deleted row when it finishes.
    conversationListVersion += 1
    conversations.value = conversations.value.filter((item: any) => String(item?.id || '') !== id)

    if (activeConversationId.value === id) {
      // Detach first so setActiveConversationId does not write the deleted
      // conversation's live state back into conversationStateById.
      activeConversationId.value = ''
      chatHistory.value = []
      liveTokenUsage.value = null
      activeConversationUsage.value = null
      activeTurnId.value = ''
      activeTurn.value = null
      activeTurnCode.value = ''
      activeTurnRelations.value = null
      finalTurnId.value = ''

      const fallback = conversations.value[0] as RecordValue | undefined
      setActiveConversationId(fallback?.id || '')
    }

    const states = { ...conversationStateById.value }
    delete states[id]
    conversationStateById.value = states
    const usageById = { ...conversationUsageById.value }
    delete usageById[id]
    conversationUsageById.value = usageById
    workspaceTurnTree.value = null
    return result
  }

  async function updateConversationTitle(title: unknown, conversationId: unknown = activeConversationId.value) {
    const id = normalizeId(conversationId)
    if (!id) return null
    const updated = await conversationApi.update(id, title)
    conversations.value = conversations.value.map((item: any) => (
      String(item?.id || '') === id ? { ...item, ...updated } : item
    ))
    return updated
  }

  function setActiveTurnPayload(turn: any) {
    activeTurn.value = turn && typeof turn === 'object' ? turn : null
    activeTurnId.value = String(turn?.id || '')
    activeTurnCode.value = String(turn?.code || '')
    if (activeConversationId.value) {
      patchConversationState(activeConversationId.value, {
        activeTurn: activeTurn.value,
        activeTurnId: activeTurnId.value,
        activeTurnCode: activeTurnCode.value,
      })
    }
  }

  async function loadActiveTurnRelations(turnId: unknown = activeTurnId.value) {
    const id = normalizeId()
    const target = String(turnId || '').trim()
    if (!id || !target) return null
    const relations = await conversationApi.relations(id, target)
    activeTurnRelations.value = relations
    setActiveTurnPayload(relations?.current || null)
    return relations
  }

  async function loadWorkspaceTurnTree(workspaceId: unknown) {
    const target = String(workspaceId || '').trim()
    if (!target) return null
    workspaceTurnTree.value = await conversationApi.workspaceTurnTree(target)
    return workspaceTurnTree.value
  }

  async function deleteTurn(turnId: unknown, conversationId: unknown = activeConversationId.value) {
    const conversation = normalizeId(conversationId)
    const turn = String(turnId || '').trim()
    if (!conversation || !turn) return
    await conversationApi.removeTurn(conversation, turn)
    await Promise.all([fetchConversationTurns({ conversationId: conversation, preferLatest: true })])
  }

  async function loadFinalTurn(conversationId: unknown = activeConversationId.value) {
    const id = normalizeId(conversationId)
    if (!id) return null
    const turn = await conversationApi.finalTurn(id)
    finalTurnId.value = String(turn?.id || '')
    return turn
  }

  async function markTurnFinal(turnId: unknown, conversationId: unknown = activeConversationId.value) {
    const id = normalizeId(conversationId)
    const target = String(turnId || '').trim()
    if (!id || !target) return null
    const turn = await conversationApi.markFinalTurn(id, target)
    finalTurnId.value = String(turn?.id || target)
    return turn
  }

  async function goToPreviousTurn() {
    const turn = activeTurnRelations.value?.previous_turn as RecordValue | undefined
    if (turn?.id) return loadActiveTurnRelations(turn.id)
    return null
  }

  async function goToNextTurn() {
    const turn = activeTurnRelations.value?.next_turn as RecordValue | undefined
    if (turn?.id) return loadActiveTurnRelations(turn.id)
    return null
  }

  function reset() {
    chatHistory.value = []
    questionHistory.value = []
    currentQuestion.value = ''
    liveTokenUsage.value = null
    activeConversationUsage.value = null
    conversationUsageById.value = {}
    conversations.value = []
    activeConversationId.value = ''
    conversationStateById.value = {}
    activeTurnId.value = ''
    activeTurn.value = null
    activeTurnCode.value = ''
    activeTurnRelations.value = null
    workspaceTurnTree.value = null
    finalTurnId.value = ''
  }

  return {
    chatHistory,
    questionHistory,
    currentQuestion,
    liveTokenUsage,
    activeConversationUsage,
    conversationUsageById,
    conversations,
    activeConversationId,
    conversationStateById,
    activeTurnId,
    activeTurn,
    activeTurnCode,
    activeTurnRelations,
    workspaceTurnTree,
    finalTurnId,
    patchConversationState,
    addChatMessage,
    addQuestionHistoryEntry,
    updateLastMessageExplanation,
    appendLastMessageExplanationChunk,
    setLastMessageCodeExplanation,
    setLastMessageAnalysisMetadata,
    appendLastMessagePlanChunk,
    appendLastMessageReasoningEvent,
    appendLastMessageTraceEvent,
    appendLastMessageToolCall,
    appendLastMessageToolProgress,
    appendLastMessageToolResult,
    markLastMessageStreamStopped,
    setLastMessageCodeSnapshot,
    setLastMessageTurnId,
    setLiveTokenUsageForCurrentTurn,
    syncLiveTokenUsageFromChatHistory,
    fetchActiveConversationUsage,
    setActiveConversationId,
    fetchConversations,
    createConversation,
    ensureActiveConversation,
    fetchConversationTurns,
    deleteConversationById,
    updateConversationTitle,
    setActiveTurnPayload,
    loadActiveTurnRelations,
    loadWorkspaceTurnTree,
    deleteTurn,
    loadFinalTurn,
    markTurnFinal,
    goToPreviousTurn,
    goToNextTurn,
    reset,
  }
})
