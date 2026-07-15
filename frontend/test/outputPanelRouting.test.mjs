import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('workspace right pane uses one result selector and routes by selected result kind', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue'),
    'utf-8',
  )

  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes('v-model="selectedResultId"'), true)
  assert.equal(source.includes('buildUnifiedResultItems'), true)
  assert.equal(source.includes("selectedResult?.kind === 'table'"), true)
  assert.equal(source.includes("selectedResult?.kind === 'chart'"), true)
  assert.equal(source.includes("selectedResult?.kind === 'log' || selectedResult?.kind === 'scalar'"), true)
  assert.equal(source.includes('<SegmentedControl'), false)
  assert.equal(source.includes('dataPaneOptions'), false)
})

test('output renderer is limited to logs and scalars without table or chart duplication', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/OutputTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes("item.kind === 'log' || item.kind === 'scalar'"), true)
  assert.equal(source.includes('Execution output'), true)
  assert.equal(source.includes('Execution error'), true)
  assert.equal(source.includes('Scalar result'), true)
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
