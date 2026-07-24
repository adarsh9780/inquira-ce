import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api service executes code through v1 workspace runtime endpoint', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiRuntime.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('/api/v1/workspaces/${activeWorkspaceId}/execute'), true)
  assert.equal(source.includes('conversation_id: appStore.activeConversationId || null'), true)
  assert.equal(source.includes('turn_id: appStore.activeTurnId || null'), true)
  assert.equal(source.includes('const persistToTurn = options?.persistToTurn !== false'), true)
  assert.equal(source.includes("const resultMode = options?.resultMode === 'jupyter' ? 'jupyter' : 'auto'"), true)
  assert.equal(source.includes('result_mode: resultMode'), true)
  assert.equal(source.includes('...(persistToTurn ? {'), true)
})

test('manual execution does not persist its artifacts into the active AI turn', () => {
  const servicePath = resolve(process.cwd(), 'src/services/executionService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes("{ persistToTurn: false, resultMode: 'jupyter' }"), true)
})
