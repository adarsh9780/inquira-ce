import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('manual execution creates a separate native turn under the current conversation', () => {
  const apiSource = readFileSync(resolve(process.cwd(), 'src/api/execution.ts'), 'utf-8')
  const goSource = readFileSync(
    resolve(process.cwd(), '..', 'internal/manualanalysis/service.go'),
    'utf-8',
  )

  assert.equal(apiSource.includes("invokeNative('RunManualCode'"), true)
  assert.equal(apiSource.includes('conversation_id: String(request.conversationId'), true)
  assert.equal(apiSource.includes('parent_turn_id: request.parentTurnId'), true)
  assert.equal(goSource.includes('UserText: "Manual code run"'), true)
  assert.equal(goSource.includes('ParentTurnID: request.ParentTurnID'), true)
  assert.equal(goSource.includes('MetadataJSON: `{"execution_source":"code_tab"}`'), true)
})
