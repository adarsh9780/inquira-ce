import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab forwards neutral sort/filter/search state to the artifact rows API', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(tableTabPath, 'utf-8')

  assert.equal(source.includes('v-model="tableSearch"'), true)
  assert.equal(source.includes(':global-filter="tableSearch"'), true)
  assert.equal(source.includes('toBackendSortModel(query)'), true)
  assert.equal(source.includes('toBackendFilterModel(query)'), true)
  assert.equal(source.includes('sortModel: toBackendSortModel(query)'), true)
  assert.equal(source.includes('filterModel: toBackendFilterModel(query)'), true)
  assert.equal(source.includes("searchText: String(tableSearch.value || '').trim()"), true)
})
