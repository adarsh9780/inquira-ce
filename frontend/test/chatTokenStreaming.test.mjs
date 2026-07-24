import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input consumes live token events and does not fall back to non-stream analyze route', () => {
  const chatInputPath = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = [
    readFileSync(chatInputPath, 'utf-8'),
    readFileSync(resolve(process.cwd(), 'src/composables/useChatStream.ts'), 'utf-8'),
  ].join('\n')

  assert.equal(source.includes("event.event === 'token'"), true)
  assert.equal(source.includes('FINAL_STREAM_NODES'), true)
  assert.equal(source.includes("'explain_code'"), true)
  assert.equal(source.includes("'noncode_generator'"), true)
  assert.equal(source.includes("'general_purpose'"), true)
  assert.equal(source.includes("'unsafe_rejector'"), true)
  assert.equal(source.includes('conversations.appendLastMessageExplanationChunk(event.data.text, messageId, options)'), true)
  assert.equal(source.includes("conversations.appendLastMessagePlanChunk(event.data.text, event.data.node || '', messageId, options)"), true)
  assert.equal(source.includes('conversations.appendLastMessageTraceEvent({'), true)
  assert.equal(source.includes('response = await apiService.v1Analyze('), false)
  assert.equal(source.includes('async function refreshRuntimeStatusAfterExplicitWork(workspaceId)'), true)
  assert.equal(source.includes('const payload = await workspaceApi.runtimeStatus(normalizedWorkspaceId)'), true)
  assert.equal(source.includes("executionStore.setWorkspaceRuntimeStatus(normalizedWorkspaceId, payload?.status || 'missing')"), true)
  assert.equal(source.includes('await refreshRuntimeStatusAfterExplicitWork(workspaceStore.activeWorkspaceId)'), true)
})
