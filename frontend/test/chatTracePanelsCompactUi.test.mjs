import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history keeps ephemeral trace hidden while preserving final response and code details', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('const SHOW_EPHEMERAL_TRACE = false'), true)
  assert.equal(source.includes('SHOW_EPHEMERAL_TRACE && ephemeralRows(message).length'), true)
  assert.equal(source.includes('(SHOW_EPHEMERAL_TRACE && hasStreamTrace(message))'), true)
  assert.equal(source.includes('Checking if query is safe to process'), true)
  assert.equal(source.includes('Final response'), true)
  assert.equal(source.includes('toggleEphemeralRow(row.id)'), true)
  assert.equal(source.includes('isEphemeralRowExpanded(row.id)'), true)
  assert.equal(source.includes('if (appStore.isLoading) return true'), true)
  assert.equal(source.includes('ephemeralExpandedRows.value.clear()'), true)
  assert.equal(source.includes('suppressMutationAutoScroll.value'), true)
  assert.equal(source.includes('ChevronRightIcon'), true)
  assert.equal(source.includes('HIDDEN_EPHEMERAL_NODES'), true)
  assert.equal(source.includes("'code_guard'"), true)
  assert.equal(source.includes("'explain_code'"), true)
  assert.equal(source.includes("stage === 'start'"), true)
  assert.equal(source.includes('Tool artifacts'), false)
  assert.equal(source.includes('View Code'), true)
  assert.equal(source.includes('Generated code details'), false)
  assert.equal(source.includes('Optional'), false)
  assert.equal(source.includes('shouldRenderCodeDetails(message)'), true)
  assert.equal(source.includes('max-height: 320px;'), true)
})
