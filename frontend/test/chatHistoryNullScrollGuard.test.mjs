import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history scrollToBottom guards null end marker after nextTick', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('const endEl = end.value'), true)
  assert.equal(source.includes('if (!endEl) return'), true)
  assert.equal(source.includes('endEl.scrollIntoView({ behavior, block: \'end\' })'), true)
})
