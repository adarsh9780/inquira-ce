import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('turn mode keeps the chat history renderer and moves navigation controls into the composer', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const chatTabSource = readFileSync(resolve(testDir, '../src/components/chat/ChatTab.vue'), 'utf-8')
  const chatHistorySource = readFileSync(resolve(testDir, '../src/components/chat/ChatHistory.vue'), 'utf-8')
  const chatInputSource = readFileSync(resolve(testDir, '../src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(chatTabSource.includes('<ChatHistory />'), true)
  assert.equal(chatTabSource.includes('TurnViewer'), false)
  assert.equal(chatHistorySource.includes('!appStore.turnViewEnabled && appStore.activeConversationId && appStore.turnsNextCursor'), true)
  assert.equal(chatInputSource.includes('@click="appStore.goToPreviousTurn()"'), true)
  assert.equal(chatInputSource.includes('@click="appStore.goToNextTurn()"'), true)
  assert.equal(chatInputSource.includes('Turn Branches'), true)
})
