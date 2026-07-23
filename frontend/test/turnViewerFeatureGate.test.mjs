import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('turn mode keeps bounded history without legacy paging or composer navigation controls', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const chatTabSource = readFileSync(resolve(testDir, '../src/components/chat/ChatTab.vue'), 'utf-8')
  const chatHistorySource = readFileSync(resolve(testDir, '../src/components/chat/ChatHistory.vue'), 'utf-8')
  const chatInputSource = readFileSync(resolve(testDir, '../src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(chatTabSource.includes('<ChatHistory />'), true)
  assert.equal(chatTabSource.includes('TurnViewer'), false)
  assert.equal(chatTabSource.includes('await appStore.fetchConversationTurns()'), true)
  assert.equal(chatHistorySource.includes('turnViewEnabled'), false)
  assert.equal(chatHistorySource.includes('turnsNextCursor'), false)
  assert.equal(chatInputSource.includes('@click="appStore.goToPreviousTurn()"'), false)
  assert.equal(chatInputSource.includes('@click="appStore.goToNextTurn()"'), false)
  assert.equal(chatInputSource.includes('title="Open turn tree"'), false)
  assert.equal(chatInputSource.includes('<TurnTreeModal'), false)
})
