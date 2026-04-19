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
  assert.equal(source.includes('class="stream-reasoning-list"'), true)
  assert.equal(source.includes('class="stream-action-section"'), true)
  assert.equal(source.includes('Final response'), true)
  assert.equal(source.includes("const eventMessage = String(event?.message || '').trim()"), true)
})

test('tool activity keeps action-detail hierarchy and renders typed output previews', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')

  assert.equal(source.includes('class="tool-activity-action"'), true)
  assert.equal(source.includes('class="tool-activity-detail"'), true)
  assert.equal(source.includes('Tool run'), false)
  assert.equal(source.includes('<TerminalRenderer'), false)
  assert.equal(source.includes('Tool input'), false)
  assert.equal(source.includes('Execution logs'), false)
  assert.equal(source.includes('JSON.stringify(toolArgs, null, 2)'), false)
  assert.equal(source.includes('<ToolOutputPreview'), true)
})

test('tool output previews collapse after newer output or final response', () => {
  const chatHistorySource = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatHistory.vue'), 'utf-8')
  const toolActivitySource = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')
  const outputPreviewSource = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolOutputPreview.vue'), 'utf-8')

  assert.equal(chatHistorySource.includes(':collapsed="isToolActivityOutputCollapsed(message, index)"'), true)
  assert.equal(chatHistorySource.includes('function isToolActivityOutputCollapsed(message, activityIndex)'), true)
  assert.equal(chatHistorySource.includes("if (String(message?.explanation || '').trim()) return true"), true)
  assert.equal(chatHistorySource.includes('.slice(activityIndex + 1)'), true)
  assert.equal(chatHistorySource.includes('.some((nextActivity) => toolOutputHasRenderableContent(nextActivity))'), true)
  assert.equal(toolActivitySource.includes(':collapsed="collapsed"'), true)
  assert.equal(outputPreviewSource.includes('collapsed: {'), true)
  assert.equal(outputPreviewSource.includes('const expanded = ref(!props.collapsed)'), true)
  assert.equal(outputPreviewSource.includes(':data-expanded="expanded ? \'true\' : \'false\'"'), true)
  assert.equal(outputPreviewSource.includes('function toggleExpanded()'), true)
})
