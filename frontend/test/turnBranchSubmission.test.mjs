import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import test from 'node:test'

test('chat input submits selected turn context and refreshes active turn on response', () => {
  const testDir = dirname(fileURLToPath(import.meta.url))
  const source = readFileSync(resolve(testDir, '../src/components/chat/ChatInput.vue'), 'utf-8')

  assert.equal(source.includes('use_selected_turn_context: Boolean(selectedParentTurnId)'), true)
  assert.equal(source.includes('selected_parent_turn_id: selectedParentTurnId || null'), true)
  assert.equal(source.includes("const responseTurnId = String(response?.turn_id || '').trim()"), true)
  assert.equal(source.includes('await appStore.loadActiveTurnRelations(responseTurnId)'), true)
})
