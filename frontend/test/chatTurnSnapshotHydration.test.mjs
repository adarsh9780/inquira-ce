import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store preserves turn code snapshot and supports ephemeral stream trace updates', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes("codeSnapshot: turn.code_snapshot || ''"), true)
  assert.equal(source.includes("codeUpdated: Boolean(String(turn.code_snapshot || '').trim())"), true)
  assert.equal(source.includes("resultExplanation: String(turn?.metadata?.result_explanation || turn.assistant_text || '')"), true)
  assert.equal(source.includes("codeExplanation: String(turn?.metadata?.code_explanation || '')"), true)
  assert.equal(source.includes('function appendLastMessageExplanationChunk(text)'), true)
  assert.equal(source.includes('function appendLastMessagePlanChunk(text, node = \'\')'), true)
  assert.equal(source.includes('function appendLastMessageTraceEvent(event)'), true)
  assert.equal(source.includes('function setLastMessageCodeSnapshot(code)'), true)
  assert.equal(source.includes('function setLastMessageCodeExplanation(explanation)'), true)
})
