import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('frontend table dependency and renderer use TanStack without AG Grid packages', () => {
  const pkg = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf-8'))
  const tableTab = readFileSync(resolve(process.cwd(), 'src/components/analysis/TableTab.vue'), 'utf-8')
  const dataTable = readFileSync(resolve(process.cwd(), 'src/components/analysis/table/DataTable.vue'), 'utf-8')

  assert.equal(Boolean(pkg.dependencies?.['@tanstack/vue-table']), true)
  assert.equal(Boolean(pkg.dependencies?.['ag-grid-community']), false)
  assert.equal(Boolean(pkg.dependencies?.['ag-grid-vue3']), false)
  assert.equal(tableTab.includes('<DataTable'), true)
  assert.equal(dataTable.includes("from '@tanstack/vue-table'"), true)
  assert.equal(dataTable.includes('getCoreRowModel: getCoreRowModel()'), true)
  assert.equal(dataTable.includes("columnResizeMode: 'onChange'"), true)
})
