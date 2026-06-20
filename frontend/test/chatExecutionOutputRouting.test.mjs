import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function extractBlock(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(start, -1, `Missing marker: ${startMarker}`)
  assert.notEqual(end, -1, `Missing marker: ${endMarker}`)
  return source.slice(start, end)
}

test('chat execution output is appended to rendered output entries', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')
  const helperBlock = extractBlock(
    source,
    'function appendChatExecutionOutput(response, conversationId = appStore.activeConversationId) {',
    'async function handleSlashCommand(questionText) {',
  )
  const submitBlock = extractBlock(
    source,
    'async function handleSubmit() {',
    '</script>',
  )

  assert.equal(helperBlock.includes('const execution = response?.execution && typeof response.execution === \'object\''), true)
  assert.equal(helperBlock.includes('appStore.appendTerminalEntry({'), true)
  assert.equal(helperBlock.includes("kind: 'output'"), true)
  assert.equal(helperBlock.includes("source: 'analysis'"), true)
  assert.equal(helperBlock.includes("label: execution.output_truncated ? 'Run output (truncated)' : 'Run output'"), true)
  assert.equal(helperBlock.includes('truncated: Boolean(execution.output_truncated)'), true)
  assert.equal(helperBlock.includes("runId: String(response?.run_id || '')"), true)
  assert.equal(helperBlock.includes('stdout,'), true)
  assert.equal(helperBlock.includes('stderr,'), true)
  assert.equal(helperBlock.includes('durationMs: Number.isFinite(Number(execution.duration_ms))'), true)
  assert.equal(submitBlock.includes('const hasChatExecutionOutput = appendChatExecutionOutput(response, requestConversationId)'), true)
  assert.equal(submitBlock.includes('} else if (hasChatExecutionOutput) {\n        applyConversationResultState(requestConversationId, finalStatePatch, { hasOutput: true })'), true)
  assert.equal(submitBlock.includes("appStore.setTerminalOutput(executionStderr || executionStdout || response.stdout || response.terminal_output || 'Code generated and executed.')"), false)
})
