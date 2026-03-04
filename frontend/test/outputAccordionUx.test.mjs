import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('output tab renders collapsible cards with header-level filters and run status metadata', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar"'), true)
  assert.equal(source.includes('class="mb-2 overflow-hidden rounded-xl border"'), true)
  assert.equal(source.includes("status === 'running'"), true)
  assert.equal(source.includes('title: `Run ${runId}`'), true)
  assert.equal(source.includes('No output generated.'), true)
  assert.equal(source.includes('toggleExpanded(event.id)'), true)
  assert.equal(source.includes("const lastAutoOpenedRunId = ref('')"), true)
  assert.equal(source.includes('watch(analysisLogEvents, (events) => {'), true)
  assert.equal(source.includes("activeFilter.value = 'all'"), true)
  assert.equal(source.includes('class="border-b px-4 py-2.5"'), false)
})
