import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history forces initial bottom scroll when mounted with hydrated turns', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(source.includes('if (displayedChatHistory.value.length > 0) {'), true)
  assert.equal(source.includes('// Hydrated conversations mount with existing messages, so force initial bottom alignment.'), true)
  assert.equal(source.includes('nextTick(() => scrollToBottom())'), true)
  assert.equal(source.includes("window.setTimeout(() => scrollToBottom({ behavior: 'auto', force: true, hardAlign: true }), 32)"), true)
})
