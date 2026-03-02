import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

test('TableTab uses AG Grid infinite model and fetches 100-row backend pages', () => {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const filePath = path.resolve(__dirname, '..', 'src', 'components', 'analysis', 'TableTab.vue')
  const source = fs.readFileSync(filePath, 'utf8')

  assert.equal(source.includes("rowModelType=\"infinite\""), true)
  assert.equal(source.includes(':paginationPageSize="pageSize"'), true)
  assert.equal(source.includes('const pageSize = 100'), true)
  assert.equal(source.includes('requestLimit = Math.max(1, Math.min(pageSize, endRow - startRow))'), true)
  assert.equal(source.includes('loadNextChunk'), false)
  assert.equal(source.includes('loadPreviousChunk'), false)
})
