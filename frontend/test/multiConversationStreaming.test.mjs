import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('store keeps conversation-scoped streaming state and per-conversation abort controllers', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/stores/appStore.js'), 'utf-8')

  assert.equal(source.includes('const conversationStateById = ref({})'), true)
  assert.equal(source.includes('function patchConversationState(conversationId, statePatch = {})'), true)
  assert.equal(source.includes('function syncActiveConversationState(options = {})'), true)
  assert.equal(source.includes('function applyConversationStateToActive(conversationId, state)'), true)
  assert.equal(source.includes('abortController: runState.abortController ? markRaw(runState.abortController)'), true)
  assert.equal(source.includes('function abortConversationRun(conversationId)'), true)
  assert.equal(source.includes('const runningConversationCount = computed(() => ('), true)
})

test('chat input routes stream events and results by conversation id', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(source.includes('appStore.addChatMessage(questionText, \'\', { attachments: attachmentsPayload, localMessageId, conversationId: requestConversationId })'), true)
  assert.equal(source.includes('abortController,'), true)
  assert.equal(source.includes('{ conversationId: requestConversationId }'), true)
  assert.equal(source.includes('applyConversationResultState(requestConversationId'), true)
  assert.equal(source.includes('requestConversationId === String(appStore.activeConversationId || \'\').trim()'), true)
  assert.equal(source.includes('appStore.patchConversationState(conversationId, { terminalOutput })'), true)
})

test('status bar summarizes multiple running conversations', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/StatusBar.vue'), 'utf-8')

  assert.equal(source.includes('const runningChats = Number(appStore.runningConversationCount || 0)'), true)
  assert.equal(source.includes('return `${runningChats} conversations running`'), true)
})
