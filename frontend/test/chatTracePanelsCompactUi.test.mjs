import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

test('chat history renders the answer first and keeps technical work in analysis details', () => {
  const chatHistoryPath = resolve(process.cwd(), 'src/components/chat/ChatHistory.vue')
  const source = readFileSync(chatHistoryPath, 'utf-8')

  assert.equal(source.includes('const SHOW_EPHEMERAL_TRACE = false'), true)
  assert.equal(source.includes('SHOW_EPHEMERAL_TRACE && ephemeralRows(message).length'), true)
  assert.equal(source.includes('(SHOW_EPHEMERAL_TRACE && hasStreamTrace(message))'), true)
  assert.equal(source.includes('Analysis details'), true)
  assert.equal(
    source.indexOf('v-if="message.explanation"') < source.indexOf('v-if="hasAnalysisDetails(message)"'),
    true,
  )
  assert.equal(source.includes('class="ephemeral-trace-list"'), true)
  assert.equal(source.includes('class="ephemeral-trace-item"'), true)
  assert.equal(source.includes('class="ephemeral-trace-action"'), true)
  assert.equal(source.includes('class="ephemeral-trace-detail"'), true)
  assert.equal(source.includes('normalizeEphemeralText(eventOutputText(event, message))'), true)
  assert.equal(source.includes('function isLikelyCodeText(text)'), true)
  assert.equal(source.includes('action: normalizeEphemeralText(action) || \'Progress\''), true)
  assert.equal(source.includes('detail,'), true)
  assert.equal(source.includes("text.startsWith('{') && text.endsWith('}')"), true)
  assert.equal(source.includes('Final response'), false)
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
  assert.equal(source.includes('>View code<'), false)
  assert.equal(source.includes('Open Code'), true)
  assert.equal(source.includes('Generated code details'), false)
  assert.equal(source.includes('Optional'), false)
  assert.equal(source.includes('class="view-code-meta-badge"'), true)
  assert.equal(source.includes('shouldRenderCodeDetails(message)'), true)
  assert.equal(source.includes('max-height: 320px;'), true)
})
