import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace right pane routes through exactly three icon-labelled result categories', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue'),
    'utf-8',
  )

  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes('v-model="selectedCategory"'), true)
  assert.equal(source.includes("selectedCategory === 'table'"), true)
  assert.equal(source.includes("selectedCategory === 'chart'"), true)
  assert.equal(source.includes("{ value: 'other', label: 'Other', icon: CommandLineIcon }"), true)
  assert.equal(source.includes('resultCategoryOptions.length'), false)
  assert.equal(source.includes('<SegmentedControl'), false)
  assert.equal(source.includes('dataPaneOptions'), false)
})

test('other renderer pairs code with non-visual output without table or chart duplication', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/OutputTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('buildOtherExecutionItems'), true)
  assert.equal(source.includes('execution.code'), true)
  assert.equal(source.includes('execution.stdout'), true)
  assert.equal(source.includes('execution.stderr'), true)
  assert.equal(source.includes('execution.scalarOutputs'), true)
  assert.equal(source.includes('Open in Table tab'), false)
  assert.equal(source.includes('Open in Chart tab'), false)
  assert.equal(source.includes('<table'), false)
})

test('manual runtime errors select their run output in the unified results pane', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('hasError: true'), true)
  assert.equal(source.includes('appStore.setSelectedResultId(resultId)'), true)
  assert.equal(source.includes('appStore.setDataPane(resultPaneForKind(selected.kind))'), true)
})
