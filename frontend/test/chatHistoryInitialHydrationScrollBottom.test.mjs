import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history forces initial bottom scroll when mounted with hydrated turns', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('if (appStore.chatHistory.length > 0) {'), true)
  assert.equal(source.includes('// Hydrated conversations mount with existing messages, so force initial bottom alignment.'), true)
  assert.equal(source.includes('nextTick(() => scrollToBottom())'), true)
})
