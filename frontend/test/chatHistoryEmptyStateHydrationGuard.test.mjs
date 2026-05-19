import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history empty state does not use v-once during async turn hydration', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(
    source.includes('v-once v-if="displayedChatHistory.length === 0 && !appStore.activeConversationIsLoading"'),
    false,
  )
  assert.equal(
    source.includes('v-if="displayedChatHistory.length === 0 && !appStore.activeConversationIsLoading"'),
    true,
  )
  assert.equal(source.includes('const syntheticMessage = mapTurnToMessage(appStore.activeTurn)'), true)
})
