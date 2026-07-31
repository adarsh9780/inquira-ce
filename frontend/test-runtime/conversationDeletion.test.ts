import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const conversationApi = vi.hoisted(() => ({
  list: vi.fn(),
  remove: vi.fn(),
}))

vi.mock('../src/api/conversations', () => ({ conversationApi }))

import { useConversationStore } from '../src/stores/conversationStore'

describe('conversation deletion', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    conversationApi.list.mockReset()
    conversationApi.remove.mockReset()
  })

  it('does not let an older list request restore a deleted conversation', async () => {
    let resolveList: (value: unknown) => void = () => {}
    conversationApi.list.mockReturnValue(new Promise((resolve) => {
      resolveList = resolve
    }))
    conversationApi.remove.mockResolvedValue({
      conversation_id: 'conversation-a',
      deleted: true,
    })

    const store = useConversationStore()
    store.conversations = [
      { id: 'conversation-a', workspace_id: 'workspace-1', title: 'Delete me' },
      { id: 'conversation-b', workspace_id: 'workspace-1', title: 'Keep me' },
    ] as any
    store.setActiveConversationId('conversation-a')
    store.addChatMessage('Question', 'Answer', { conversationId: 'conversation-a' })

    const staleListRequest = store.fetchConversations('workspace-1')
    await store.deleteConversationById('conversation-a')
    resolveList({
      conversations: [
        { id: 'conversation-a', workspace_id: 'workspace-1', title: 'Delete me' },
        { id: 'conversation-b', workspace_id: 'workspace-1', title: 'Keep me' },
      ],
    })
    await staleListRequest

    expect(conversationApi.remove).toHaveBeenCalledWith('conversation-a')
    expect(store.conversations.map((conversation) => conversation.id)).toEqual(['conversation-b'])
    expect(store.activeConversationId).toBe('conversation-b')
    expect(store.conversationStateById).not.toHaveProperty('conversation-a')
  })
})
