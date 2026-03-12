import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table pagination avoids extra row animation churn and redundant viewport persistence updates', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')

  const tableTab = readFileSync(tableTabPath, 'utf-8')
  const store = readFileSync(storePath, 'utf-8')

  assert.equal(tableTab.includes(':animateRows="false"'), true)
  assert.equal(tableTab.includes(':animateRows="true"'), false)
  assert.equal(store.includes('function setTableViewport(start, end, total) {'), true)
  assert.equal(store.includes('tableWindowStart.value === nextStart'), true)
  assert.equal(store.includes('tableWindowEnd.value === nextEnd'), true)
  assert.equal(store.includes('tableRowCount.value === nextTotal'), true)
  assert.equal(store.includes('if (Number(tablePageOffsets.value?.[key] || 0) === normalizedPage) return'), true)
})
