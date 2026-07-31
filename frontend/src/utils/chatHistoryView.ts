type RecordValue = Record<string, any>

function normalizedId(value: unknown) {
  return String(value || '').trim()
}

function firstNonEmptyText(...values: unknown[]) {
  for (const value of values) {
    const text = String(value || '').trim()
    if (text) return text
  }
  return ''
}

export function mapTurnToChatMessage(turn: unknown) {
  if (!turn || typeof turn !== 'object') return null
  const value = turn as RecordValue
  const metadata = value.metadata && typeof value.metadata === 'object'
    ? value.metadata as RecordValue
    : {}
  const finalResponse = metadata.final_response && typeof metadata.final_response === 'object'
    ? metadata.final_response as RecordValue
    : {}
  const explanation = firstNonEmptyText(
    value.assistant_text,
    value.answer,
    finalResponse.answer,
    metadata.result_explanation,
  )
  return {
    id: value.id,
    turnId: normalizedId(value.id),
    question: String(value.user_text || value.question || ''),
    explanation,
    resultExplanation: firstNonEmptyText(metadata.result_explanation, explanation),
    codeExplanation: String(metadata.code_explanation || ''),
    analysisMetadata: { ...metadata },
    attachments: Array.isArray(metadata.user_attachments)
      ? metadata.user_attachments.map((item: any) => ({ ...item }))
      : [],
    toolEvents: Array.isArray(value.tool_events)
      ? value.tool_events.map((event: any) => ({ ...event }))
      : null,
    streamTrace: null,
    codeSnapshot: String(value.code_snapshot || value.code || ''),
    codeUpdated: Boolean(String(value.code_snapshot || value.code || '').trim()),
    timestamp: value.created_at || new Date().toISOString(),
  }
}

export function messageMatchesTurn(message: unknown, turnId: unknown) {
  if (!message || typeof message !== 'object') return false
  const target = normalizedId(turnId)
  if (!target) return false
  const value = message as RecordValue
  return normalizedId(value.id) === target || normalizedId(value.turnId) === target
}

export function selectDisplayedChatHistory({
  localHistory,
  activeTurnId,
  activeTurn,
  isRunning,
}: {
  localHistory: unknown
  activeTurnId: unknown
  activeTurn: unknown
  isRunning: boolean
}) {
  const local = Array.isArray(localHistory) ? localHistory : []
  const selectedTurnId = normalizedId(activeTurnId)

  if (isRunning && local.length > 0) {
    const pendingMessage = local[local.length - 1]
    if (!selectedTurnId || !messageMatchesTurn(pendingMessage, selectedTurnId)) {
      return [pendingMessage]
    }
  }

  if (selectedTurnId) {
    const existing = local.find((message) => messageMatchesTurn(message, selectedTurnId))
    if (existing) return [existing]
  }

  const syntheticMessage = mapTurnToChatMessage(activeTurn)
  return syntheticMessage ? [syntheticMessage] : []
}
