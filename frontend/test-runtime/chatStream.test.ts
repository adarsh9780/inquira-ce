import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { extractLangGraphTokenText, useChatStream } from '../src/composables/useChatStream'
import { useConversationStore } from '../src/stores/conversationStore'

describe('chat stream coordinator', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('extracts nested LangGraph message content', () => {
    expect(extractLangGraphTokenText([{ content: [{ type: 'text', text: 'hello' }] }])).toBe('hello')
  })

  it('routes final and planning tokens to the scoped conversation', () => {
    const conversations = useConversationStore()
    conversations.chatHistory = [{ id: 'message-a', explanation: '', streamTrace: { planText: '' } }]
    conversations.activeConversationId = 'conversation-a'
    const stream = useChatStream(conversations, () => 'normalized error')

    stream.applyStreamEvent(
      { event: 'token', data: { node: 'planner', text: 'inspect schema' } },
      'message-a',
      'conversation-a',
    )
    stream.applyStreamEvent(
      { event: 'token', data: { node: 'finalize', text: 'answer' } },
      'message-a',
      'conversation-a',
    )

    expect(conversations.chatHistory[0]?.streamTrace?.planText).toContain('inspect schema')
    expect(conversations.chatHistory[0]?.explanation).toContain('answer')
  })
})
