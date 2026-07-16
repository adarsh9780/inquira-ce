import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('runs render one expandable side-by-side block with every output kind', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const source = readFileSync(outputTabPath, 'utf-8')

  assert.equal(source.includes('Teleport to="#workspace-right-pane-toolbar-right"'), true)
  assert.equal(source.includes('v-for="execution in executionItems"'), true)
  assert.equal(source.includes('data-runs-feed'), true)
  assert.equal(source.includes('data-user-run'), true)
  assert.equal(source.includes('data-run-body'), true)
  assert.equal(source.includes('data-execution-code'), true)
  assert.equal(source.includes('data-execution-stdout'), true)
  assert.equal(source.includes('data-execution-stderr'), true)
  assert.equal(source.includes('buildUserRunItems'), true)
  assert.equal(source.includes('<RunTableOutput'), true)
  assert.equal(source.includes('<RunChartOutput'), true)
  assert.equal(source.includes('Replace current table'), true)
  assert.equal(source.includes('Replace current chart'), true)
  assert.equal(source.includes('divide-y'), true)
  assert.equal(source.includes('rounded-xl'), false)
  assert.equal(source.includes('<HeaderDropdown'), false)
  assert.equal(source.includes('md:grid-cols-[minmax(15rem,0.85fr)_minmax(0,1.15fr)]'), true)
  assert.equal(source.includes('buildUnifiedResultItems'), false)
})
