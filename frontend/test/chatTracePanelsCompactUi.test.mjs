import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat history renders subdued reasoning blocks before final response and keeps code details lightweight', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('const SHOW_EPHEMERAL_TRACE = true'), true)
  assert.equal(source.includes('SHOW_EPHEMERAL_TRACE && ephemeralRows(message).length'), true)
  assert.equal(source.includes('(SHOW_EPHEMERAL_TRACE && hasStreamTrace(message))'), true)
  assert.equal(source.includes('Checking if query is safe to process'), true)
  assert.equal(source.includes('class="ephemeral-trace-row"'), true)
  assert.equal(source.includes('class="ephemeral-trace-prefix"'), true)
  assert.equal(source.includes('normalizeEphemeralText(eventOutputText(event, message))'), true)
  assert.equal(source.includes("text: output || fallbackSummary || 'Processing update'"), true)
  assert.equal(source.includes("text.startsWith('{') && text.endsWith('}')"), true)
  assert.equal(source.includes('Final response'), true)
  assert.equal(source.includes('toggleEphemeralRow(row.id)'), false)
  assert.equal(source.includes('isEphemeralRowExpanded(row.id)'), false)
  assert.equal(source.includes('ephemeralExpandedRows.value.clear()'), false)
  assert.equal(source.includes('suppressMutationAutoScroll.value'), false)
  assert.equal(source.includes('HIDDEN_EPHEMERAL_NODES'), true)
  assert.equal(source.includes("'code_guard'"), true)
  assert.equal(source.includes("'explain_code'"), true)
  assert.equal(source.includes("stage === 'start'"), true)
  assert.equal(source.includes('class="thinking-block"'), false)
  assert.equal(source.includes('class="thinking-toggle"'), false)
  assert.equal(source.includes('class="thinking-static"'), false)
  assert.equal(source.includes('Tool artifacts'), false)
  assert.equal(source.includes('&lt;/&gt; View code'), false)
  assert.equal(source.includes('>View code<'), true)
  assert.equal(source.includes('Generated code details'), false)
  assert.equal(source.includes('Optional'), false)
  assert.equal(source.includes('class="view-code-meta-badge"'), true)
  assert.equal(source.includes('shouldRenderCodeDetails(message)'), true)
  assert.equal(source.includes('max-height: 320px;'), true)
})
