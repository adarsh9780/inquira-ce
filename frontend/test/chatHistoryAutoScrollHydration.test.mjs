import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history scroll logic restores auto-scroll for hydrated conversations', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('const previousLength = Number.isFinite(oldLength) ? oldLength : 0'), true)
  assert.equal(source.includes('watch(() => appStore.activeConversationId, () => {'), true)
  assert.equal(source.includes('shouldAutoScroll = true'), true)
  assert.equal(source.includes('nextTick(() => scrollToBottom())'), true)
})
