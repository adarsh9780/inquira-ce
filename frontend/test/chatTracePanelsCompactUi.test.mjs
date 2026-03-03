import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history renders visible ephemeral summaries, final separator, and scrollable code blocks', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('Checking if query is safe to process'), true)
  assert.equal(source.includes('Final response'), true)
  assert.equal(source.includes('View plan output'), true)
  assert.equal(source.includes('class="chat-code-block mt-3"'), true)
  assert.equal(source.includes('max-h-52 overflow-auto'), true)
  assert.equal(source.includes('max-height: 320px;'), true)
})
