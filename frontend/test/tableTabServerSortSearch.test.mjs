import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab forwards AG Grid sort/filter/search state to artifact rows API', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(tableTabPath, 'utf-8')

  assert.equal(source.includes('v-model="tableSearch"'), true)
  assert.equal(source.includes(':quickFilterText="tableSearch"'), true)
  assert.equal(source.includes('const sortModel = Array.isArray(params?.sortModel) ? params.sortModel : []'), true)
  assert.equal(source.includes('const filterModel = ('), true)
  assert.equal(source.includes('sortModel,'), true)
  assert.equal(source.includes('filterModel,'), true)
  assert.equal(source.includes("searchText: String(tableSearch.value || '').trim()"), true)
})
