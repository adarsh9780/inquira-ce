import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table pagination avoids extra row animation churn and redundant viewport persistence updates', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const dataTablePath = resolve(process.cwd(), 'src/components/analysis/table/DataTable.vue')
  const storePath = resolve(process.cwd(), 'src/stores/appCoordinatorStore.js')

  const tableTab = readFileSync(tableTabPath, 'utf-8')
  const dataTable = readFileSync(dataTablePath, 'utf-8')
  const store = readFileSync(storePath, 'utf-8')

  assert.equal(tableTab.includes('<ag-grid-vue'), false)
  assert.equal(tableTab.includes('currentPageRequestToken'), true)
  assert.equal(dataTable.includes('getPaginationRowModel: getPaginationRowModel()'), true)
  assert.equal(dataTable.includes(':disabled="!table.getCanNextPage() || loading"'), true)
  assert.equal(store.includes('function setTableViewport(start, end, total) {'), true)
  assert.equal(store.includes('tableWindowStart.value === nextStart'), true)
  assert.equal(store.includes('tableWindowEnd.value === nextEnd'), true)
  assert.equal(store.includes('tableRowCount.value === nextTotal'), true)
  assert.equal(store.includes('if (Number(tablePageOffsets.value?.[key] || 0) === normalizedPage) return'), true)
})
