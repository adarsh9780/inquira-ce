import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useConversationStore } from '../src/stores/conversationStore'

describe('conversationStore', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('keeps simultaneous conversation stream mutations isolated', () => {
    const store = useConversationStore()
    store.setActiveConversationId('conversation-a')
    const first = store.addChatMessage('A', '', { conversationId: 'conversation-a' })
    store.addChatMessage('B', '', { conversationId: 'conversation-b', localMessageId: 'message-b' })
    store.appendLastMessageExplanationChunk('answer-a', first, { conversationId: 'conversation-a' })
    store.appendLastMessageExplanationChunk('answer-b', 'message-b', { conversationId: 'conversation-b' })
    expect(store.chatHistory[0]).toMatchObject({ explanation: 'answer-a' })
    store.setActiveConversationId('conversation-b')
    expect(store.chatHistory[0]).toMatchObject({ explanation: 'answer-b' })
  })

  it('caps and deduplicates question history', () => {
    const store = useConversationStore()
    for (let index = 0; index < 35; index += 1) store.addQuestionHistoryEntry(`question-${index}`)
    store.addQuestionHistoryEntry('question-30')
    expect(store.questionHistory).toHaveLength(30)
    expect(store.questionHistory[0]).toBe('question-30')
  })

  it('does not erase a streamed assistant answer when completion text is empty', () => {
    const store = useConversationStore()
    store.setActiveConversationId('conversation-a')
    const messageId = store.addChatMessage('Question', '', { conversationId: 'conversation-a' })
    store.appendLastMessageExplanationChunk('Streamed answer', messageId, { conversationId: 'conversation-a' })

    expect(store.finalizeLastMessageExplanation('', messageId, { conversationId: 'conversation-a' })).toBe(false)
    expect(store.chatHistory[0]?.explanation).toBe('Streamed answer')

    expect(store.finalizeLastMessageExplanation('Final answer', messageId, { conversationId: 'conversation-a' })).toBe(true)
    expect(store.chatHistory[0]?.explanation).toBe('Final answer')
  })
})
