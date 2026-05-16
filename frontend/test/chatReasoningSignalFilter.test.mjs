import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat reasoning hides generic schema routing text and supports has-wants-next sections', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(source.includes('const GENERIC_REASONING_PATTERNS = ['), true)
  assert.equal(source.includes("'assessing schema context'"), true)
  assert.equal(source.includes("'deciding whether more schema/data lookup is required before code generation'"), true)
  assert.equal(source.includes('function isGenericReasoningMessage(message) {'), true)
  assert.equal(source.includes('.filter((row) => row.message && !isGenericReasoningMessage(row.message))'), true)
  assert.equal(source.includes('function parseReasoningSections(message) {'), true)
  assert.equal(source.includes('function inferReasoningSectionsFromSentences(text) {'), true)
  assert.equal(source.includes("label: REASONING_SECTION_LABELS.has"), true)
  assert.equal(source.includes("label: REASONING_SECTION_LABELS.wants"), true)
  assert.equal(source.includes("label: REASONING_SECTION_LABELS.next"), true)
  assert.equal(source.includes('class="stream-reasoning-section"'), true)
})
