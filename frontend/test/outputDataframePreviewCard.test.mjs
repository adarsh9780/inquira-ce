import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('manual dataframes render inline in Runs and only become full tables after promotion', () => {
  const outputTabPath = resolve(process.cwd(), 'src/components/analysis/OutputTab.vue')
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const rightPanePath = resolve(process.cwd(), 'src/components/layout/WorkspaceRightPane.vue')
  const output = readFileSync(outputTabPath, 'utf-8')
  const table = readFileSync(tableTabPath, 'utf-8')
  const rightPane = readFileSync(rightPanePath, 'utf-8')

  assert.equal(output.includes('<RunTableOutput'), true)
  assert.equal(output.includes('promoteUserRunTable'), true)
  assert.equal(output.includes('buildDataframePreview'), false)
  assert.equal(table.includes('<DataTable'), true)
  assert.equal(table.includes(':manual="useServerModel"'), true)
  assert.equal(rightPane.includes("selectedCategory === 'table'"), true)
  assert.equal(table.includes('appStore.promotedUserDataframes'), true)
})
