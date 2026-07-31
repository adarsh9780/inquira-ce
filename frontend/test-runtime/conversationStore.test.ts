import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import ConversationSwitcher from '../src/components/layout/ConversationSwitcher.vue'
import { useConversationStore } from '../src/stores/conversationStore'
import { useUiStore } from '../src/stores/uiStore'
import { useWorkspaceStore } from '../src/stores/workspaceStore'
import { conversationApi } from '../src/api/conversations'

describe('conversationStore', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => {
    vi.restoreAllMocks()
    document.body.innerHTML = ''
  })

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

  it('starts a local draft and creates it only when submission needs an id', async () => {
    const create = vi.spyOn(conversationApi, 'create').mockResolvedValue({
      id: 'conversation-new',
      workspace_id: 'workspace-1',
      title: 'New chat',
    } as any)
    const store = useConversationStore()
    store.setActiveConversationId('conversation-old')
    store.addChatMessage('Old question', 'Old answer')
    store.currentQuestion = 'unfinished text'

    store.startConversationDraft()

    expect(store.activeConversationId).toBe('')
    expect(store.chatHistory).toEqual([])
    expect(store.currentQuestion).toBe('')
    expect(create).not.toHaveBeenCalled()

    await expect(store.ensureActiveConversation('workspace-1', 'New chat')).resolves.toBe('conversation-new')
    expect(create).toHaveBeenCalledOnce()
  })

  it('switches saved conversations and starts a local draft from the top bar', async () => {
    const listTurns = vi.spyOn(conversationApi, 'listTurns').mockResolvedValue({ turns: [] } as any)
    const workspaceStore = useWorkspaceStore()
    const conversationStore = useConversationStore()
    const uiStore = useUiStore()
    workspaceStore.workspaces = [{ id: 'workspace-1', name: 'Cricket' }] as any
    workspaceStore.setActiveWorkspaceId('workspace-1')
    conversationStore.conversations = [
      { id: 'conversation-a', workspace_id: 'workspace-1', title: 'First analysis' },
      { id: 'conversation-b', workspace_id: 'workspace-1', title: 'Second analysis' },
    ] as any
    conversationStore.setActiveConversationId('conversation-a')

    const wrapper = mount(ConversationSwitcher, { attachTo: document.body })
    await wrapper.get('button').trigger('click')
    await vi.waitFor(() => expect(document.body.textContent).toContain('Second analysis'))

    expect(uiStore.isConversationSwitcherOpen).toBe(true)
    const second = [...document.body.querySelectorAll<HTMLElement>('[role="option"]')]
      .find((option) => option.textContent?.includes('Second analysis'))
    expect(second).toBeTruthy()
    second?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await vi.waitFor(() => expect(listTurns).toHaveBeenCalledWith('conversation-b', 50))
    expect(conversationStore.activeConversationId).toBe('conversation-b')
    expect(uiStore.isConversationSwitcherOpen).toBe(false)

    await vi.waitFor(() => expect(wrapper.get('button').attributes('disabled')).toBeUndefined())
    await wrapper.get('button').trigger('click')
    await vi.waitFor(() => expect(document.body.textContent).toContain('Start with a blank analysis'))
    const create = [...document.body.querySelectorAll<HTMLElement>('[role="option"]')]
      .find((option) => option.textContent?.includes('Start with a blank analysis'))
    expect(create).toBeTruthy()
    create?.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(conversationStore.activeConversationId).toBe('')
    expect(listTurns).toHaveBeenCalledOnce()
    expect(wrapper.get('button').text()).toContain('New conversation')
    wrapper.unmount()
  })
})
