import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat trace uses plain muted text rows without expandable output payloads', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')

  assert.equal(source.includes('class="ephemeral-trace-list"'), true)
  assert.equal(source.includes('class="ephemeral-trace-item"'), true)
  assert.equal(source.includes('class="ephemeral-trace-action"'), true)
  assert.equal(source.includes('class="ephemeral-trace-detail"'), true)
  assert.equal(source.includes('renderMarkdown(row.output)'), false)
  assert.equal(source.includes('toggleEphemeralRow(row.id)'), false)
  assert.equal(source.includes('isEphemeralRowExpanded(row.id)'), false)
  assert.equal(source.includes('normalizeEphemeralText('), true)
  assert.equal(source.includes('function isLikelyCodeText(text)'), true)
  assert.equal(source.includes('if (isLikelyCodeText(text)) return \'\''), true)
})

test('tool activity keeps action-detail hierarchy and avoids raw json panels', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')

  assert.equal(source.includes('class="tool-activity-action"'), true)
  assert.equal(source.includes('class="tool-activity-detail"'), true)
  assert.equal(source.includes('Tool run'), true)
  assert.equal(source.includes('<TerminalRenderer'), false)
  assert.equal(source.includes('Tool input'), false)
  assert.equal(source.includes('Execution logs'), false)
  assert.equal(source.includes('JSON.stringify(toolArgs, null, 2)'), false)
})
