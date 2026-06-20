import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat input surfaces backend error detail instead of flattening 5xx into generic copy', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(source.includes("const backendDetail = extractApiErrorMessage(error, '')"), true)
  assert.equal(source.includes("errorTitle = 'Backend Error'"), true)
  assert.equal(source.includes("errorMessage = backendDetail || 'The server encountered an error. Please try again later.'"), true)
  assert.equal(source.includes("source: status > 0 ? 'Backend' : 'Frontend'"), true)
  assert.equal(source.includes("category: 'llm_api'"), true)
  assert.equal(source.includes("if (evt.event === 'error')"), true)
  assert.equal(source.includes("appStore.updateLastMessageExplanation(streamErrorMessage, localMessageId, { conversationId: requestConversationId })"), true)
})
