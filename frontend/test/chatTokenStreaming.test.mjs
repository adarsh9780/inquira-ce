import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input consumes live token events and does not fall back to non-stream analyze route', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(chatInputPath, 'utf-8')

  assert.equal(source.includes("evt.event === 'token'"), true)
  assert.equal(source.includes('FINAL_STREAM_NODES'), true)
  assert.equal(source.includes("'explain_code'"), true)
  assert.equal(source.includes("'noncode_generator'"), true)
  assert.equal(source.includes("'general_purpose'"), true)
  assert.equal(source.includes("'unsafe_rejector'"), true)
  assert.equal(source.includes('appStore.appendLastMessageExplanationChunk(evt.data.text, localMessageId, { conversationId: requestConversationId })'), true)
  assert.equal(source.includes("appStore.appendLastMessagePlanChunk(evt.data.text, evt.data.node || '', localMessageId, { conversationId: requestConversationId })"), true)
  assert.equal(source.includes('appStore.appendLastMessageTraceEvent({'), true)
  assert.equal(source.includes('response = await apiService.v1Analyze('), false)
  assert.equal(source.includes('async function refreshRuntimeStatusAfterExplicitWork(workspaceId)'), true)
  assert.equal(source.includes('const payload = await apiService.v1GetWorkspaceRuntimeStatus(normalizedWorkspaceId)'), true)
  assert.equal(source.includes("appStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, payload?.status || 'missing')"), true)
  assert.equal(source.includes('await refreshRuntimeStatusAfterExplicitWork(appStore.activeWorkspaceId)'), true)
})
