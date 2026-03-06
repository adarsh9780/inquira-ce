import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('tool activity card summarizes tool inputs with collapsible details', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/chat/ToolActivityCard.vue'), 'utf-8')

  assert.equal(source.includes('detailsOpen = ref(false)'), true)
  assert.equal(source.includes('const hasDetails = computed(() => hasArgs.value || hasLines.value)'), true)
  assert.equal(source.includes('Tool input'), true)
  assert.equal(source.includes('Execution logs'), true)
  assert.equal(source.includes('Looking for ${columnText} in ${table} using ${tool} tool'), true)
  assert.equal(source.includes('Sampling ${limit} rows from ${table} using ${tool} tool'), true)
  assert.equal(source.includes('Running "${command}" using ${tool} tool'), true)
  assert.equal(source.includes("['bash', 'pip_install'].includes(normalizedToolName.value)"), true)
  assert.equal(source.includes('tool-activity-summary-running'), true)
  assert.equal(source.includes('@keyframes tool-running-shine'), true)
  assert.equal(source.includes('tool-activity-status'), false)
  assert.equal(source.includes('formattedOutput'), false)
})
