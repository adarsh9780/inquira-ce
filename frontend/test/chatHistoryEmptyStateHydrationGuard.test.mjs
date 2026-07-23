import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history leaves empty guidance to ChatTab while preserving hydration and loading states', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(source.includes('displayedChatHistory.length === 0 && !appStore.activeConversationIsLoading'), false)
  assert.equal(source.includes('appStore.activeConversationIsLoading && displayedChatHistory.length === 0'), true)
  assert.equal(source.includes('const syntheticMessage = mapTurnToMessage(appStore.activeTurn)'), true)
})
