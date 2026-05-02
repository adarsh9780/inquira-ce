import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('turn viewer is feature-gated from chat tab and exposes navigation controls', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const chatTabSource = readFileSync(resolve(testDir, '../src/components/chat/ChatTab.vue'), 'utf-8')
  const turnViewerSource = readFileSync(resolve(testDir, '../src/components/chat/TurnViewer.vue'), 'utf-8')

  assert.equal(chatTabSource.includes('<TurnViewer v-if="appStore.turnViewEnabled" />'), true)
  assert.equal(turnViewerSource.includes('@click="appStore.goToPreviousTurn()"'), true)
  assert.equal(turnViewerSource.includes('@click="appStore.goToNextTurn()"'), true)
  assert.equal(turnViewerSource.includes('@change="handleBranchPick"'), true)
  assert.equal(turnViewerSource.includes('Final Turn'), true)
  assert.equal(turnViewerSource.includes('@click="appStore.markActiveTurnFinal()"'), true)
})
