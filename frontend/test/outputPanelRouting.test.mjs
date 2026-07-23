import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace right pane routes through exactly three icon-labelled result categories', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue'),
    'utf-8',
  )

  assert.equal(source.includes('<SegmentedControl'), true)
  assert.equal(source.includes('<HeaderDropdown'), false)
  assert.equal(source.includes('v-model="selectedCategory"'), true)
  assert.equal(source.includes("selectedCategory === 'table'"), true)
  assert.equal(source.includes("selectedCategory === 'chart'"), true)
  assert.equal(source.includes("{ value: 'runs', label: 'Runs', icon: PlayCircleIcon, count: runResultCount.value }"), true)
  assert.equal(source.includes('resultCategoryOptions.length'), false)
  assert.equal(source.includes('dataPaneOptions'), false)
})

test('runs renderer pairs code with text, table, and chart output in one block', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/OutputTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('buildUserRunItems'), true)
  assert.equal(source.includes('selectedExecution.code'), true)
  assert.equal(source.includes('selectedExecution.stdout'), true)
  assert.equal(source.includes('selectedExecution.stderr'), true)
  assert.equal(source.includes('selectedExecution.scalarOutputs'), true)
  assert.equal(source.includes('selectedExecution.tableOutputs'), true)
  assert.equal(source.includes('selectedExecution.chartOutputs'), true)
  assert.equal(source.includes('<RunTableOutput'), true)
  assert.equal(source.includes('<RunChartOutput'), true)
})

test('manual runtime errors always select Runs', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('appStore.setSelectedResultId(executionLogResultId(effectiveRunEntryId))'), true)
  assert.equal(source.includes("appStore.setDataPane('output')"), true)
  assert.equal(source.includes('resultPaneForKind'), false)
})
