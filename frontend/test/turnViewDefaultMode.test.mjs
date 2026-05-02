import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('turn-first mode is the default and selected-turn context no longer depends on a feature flag', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const storeSource = readFileSync(resolve(testDir, '../src/stores/appStore.js'), 'utf-8')
  const inputSource = readFileSync(resolve(testDir, '../src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(storeSource.includes('const turnViewEnabled = ref(true)'), true)
  assert.equal(inputSource.includes("const selectedParentTurnId = String(appStore.activeTurnId || '').trim()"), true)
  assert.equal(inputSource.includes('use_selected_turn_context: Boolean(selectedParentTurnId)'), true)
})
