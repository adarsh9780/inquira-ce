import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('tool activity card keeps simple muted summaries without expandable raw-json details', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')

  assert.equal(source.includes('detailsOpen = ref(false)'), false)
  assert.equal(source.includes('class="tool-activity-toggle"'), false)
  assert.equal(source.includes('Tool input'), false)
  assert.equal(source.includes('Execution logs'), false)
  assert.equal(source.includes('class="tool-activity-prefix"'), false)
  assert.equal(source.includes(':aria-label="`${summaryText} (${statusLabel})`"'), false)
  assert.equal(source.includes('Looking for ${columnText} in ${table} using ${tool} tool'), true)
  assert.equal(source.includes('Sampling ${limit} rows from ${table} using ${tool} tool'), true)
  assert.equal(source.includes("isComplete ? 'Ran' : 'Running'"), true)
  assert.equal(source.includes('tool-activity-summary-running'), true)
  assert.equal(source.includes('@keyframes tool-running-shine'), false)
  assert.equal(source.includes('tool-activity-status'), false)
  assert.equal(source.includes('formattedArgs'), false)
  assert.equal(source.includes('formattedLines'), false)
})
