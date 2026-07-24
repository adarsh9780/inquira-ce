import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('selected-turn context is always available without a feature flag', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const storeSource = readFileSync(resolve(testDir, '../src/stores/conversationStore.ts'), 'utf-8')
  const inputSource = readFileSync(resolve(testDir, '../src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(storeSource.includes('turnViewEnabled'), false)
  assert.equal(inputSource.includes("const selectedParentTurnId = String(conversationStore.activeTurnId || '').trim()"), true)
  assert.equal(inputSource.includes('use_selected_turn_context: Boolean(selectedParentTurnId)'), true)
})
