import { invokeNative, nativeApp } from './native.ts'

type RecordValue = Record<string, unknown>

export function normalizeNativeTurn(turn: unknown): RecordValue | null {
  if (!turn || typeof turn !== 'object') return null
  const value = turn as RecordValue
  const parse = (candidate: unknown, fallback: unknown) => {
    if (typeof candidate !== 'string' || !candidate.trim()) return fallback
    try {
      return JSON.parse(candidate)
    } catch {
      return fallback
    }
  }
  return {
    ...value,
    metadata: parse(value.metadata_json, {}),
    tool_events: parse(value.tool_events_json, []),
    result: parse(value.result_json, null),
  }
}

function nativeTurnTree(turns: unknown[]) {
  const normalized = turns.map(normalizeNativeTurn).filter(Boolean) as RecordValue[]
  const nodes = new Map(normalized.map((turn) => [String(turn.id), {
    ...turn,
    display_no: Number(turn.sequence || 0),
    usage: (turn.metadata as RecordValue | undefined)?.token_usage || null,
    children: [] as RecordValue[],
  }]))
  const roots: RecordValue[] = []
  for (const turn of normalized) {
    const node = nodes.get(String(turn.id))
    if (!node) continue
    const parent = turn.parent_turn_id ? nodes.get(String(turn.parent_turn_id)) : null
    if (parent) parent.children.push(node)
    else roots.push(node)
  }
  const compare = (left: RecordValue, right: RecordValue) => (
    Number(left.sibling_order || 0) - Number(right.sibling_order || 0)
    || Number(left.sequence || 0) - Number(right.sequence || 0)
  )
  roots.sort(compare)
  for (const node of nodes.values()) node.children.sort(compare)
  return { turns: normalized, roots }
}

export const conversationApi = {
  async list(workspaceId: unknown, limit = 50) {
    const response = await invokeNative('ListConversations', String(workspaceId || ''))
    const value = response as RecordValue
    const conversations = Array.isArray(response) ? response : (value?.conversations || [])
    return { conversations: (conversations as unknown[]).slice(0, Number(limit || 50)) }
  },
  create(workspaceId: unknown, title: unknown = null) {
    return invokeNative('CreateConversation', {
      workspace_id: String(workspaceId || ''),
      title: String(title || 'New conversation'),
    })
  },
  remove(conversationId: unknown) {
    return invokeNative('DeleteConversation', String(conversationId || ''))
  },
  update(conversationId: unknown, title: unknown) {
    return invokeNative(
      'UpdateConversation',
      String(conversationId || ''),
      String(title || ''),
    )
  },
  usage(conversationId: unknown) {
    return invokeNative('GetConversationUsage', String(conversationId || ''))
  },
  async listTurns(conversationId: unknown, limit = 5) {
    const page = await invokeNative(
      'ListConversationTurnPage',
      String(conversationId || ''),
      Number(limit || 5),
      '',
    )
    return {
      turns: (Array.isArray(page?.turns) ? page.turns : [])
        .map(normalizeNativeTurn)
        .filter(Boolean),
    }
  },
  async getTurn(_conversationId: unknown, turnId: unknown) {
    return normalizeNativeTurn(await invokeNative('GetConversationTurn', String(turnId || '')))
  },
  async relations(conversationId: unknown, turnId: unknown) {
    const raw = await invokeNative('ListConversationTurns', String(conversationId || ''))
    const turns = raw.map(normalizeNativeTurn).filter(Boolean) as RecordValue[]
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
  async workspaceTurnTree(workspaceId: unknown) {
    const response = await invokeNative('ListConversations', String(workspaceId || ''))
    const value = response as RecordValue
    const conversations = (Array.isArray(response) ? response : (value?.conversations || [])) as RecordValue[]
    const app = nativeApp()
    return {
      workspace_id: String(workspaceId || ''),
      conversations: await Promise.all(conversations.map(async (item) => {
        const tree = nativeTurnTree(await invokeNative('ListConversationTurns', String(item.id || '')))
        const usageSummary = typeof app?.GetConversationUsage === 'function'
          ? await app.GetConversationUsage(String(item.id || ''))
          : null
        return { ...item, roots: tree.roots, final_turn_id: item.final_turn_id || null, usage_summary: usageSummary }
      })),
    }
  },
  removeTurn(conversationId: unknown, turnId: unknown) {
    return invokeNative(
      'DeleteConversationTurn',
      String(conversationId || ''),
      String(turnId || ''),
    )
  },
  async finalTurn(conversationId: unknown) {
    const result = await invokeNative('GetFinalConversationTurn', String(conversationId || ''))
    return result ? normalizeNativeTurn(result) : null
  },
  async markFinalTurn(conversationId: unknown, turnId: unknown) {
    return normalizeNativeTurn(await invokeNative(
      'MarkFinalConversationTurn',
      String(conversationId || ''),
      String(turnId || ''),
    ))
  },
}
