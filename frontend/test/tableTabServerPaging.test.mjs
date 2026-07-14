import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

test('TableTab uses the TanStack data table and fetches 100-row backend pages', () => {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const filePath = path.resolve(__dirname, '..', 'src', 'components', 'analysis', 'TableTab.vue')
  const source = fs.readFileSync(filePath, 'utf8')

  assert.equal(source.includes('<DataTable'), true)
  assert.equal(source.includes(':manual="useServerModel"'), true)
  assert.equal(source.includes('const pageSize = DEFAULT_TABLE_PAGE_SIZE'), true)
  assert.equal(source.includes('const startRow = pageIndex * requestLimit'), true)
  assert.equal(source.includes('requestLimit = Math.max(1, Math.min(pageSize,'), true)
  assert.equal(source.includes('<ag-grid-vue'), false)
  assert.equal(source.includes('loadNextChunk'), false)
  assert.equal(source.includes('loadPreviousChunk'), false)
})
