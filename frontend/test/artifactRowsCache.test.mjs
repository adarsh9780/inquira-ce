import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native artifact rows are cached by artifact, page, and query state', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/apiService.js'),
    'utf8',
  )

  assert.equal(source.includes('const artifactRowsCache = new Map()'), true)
  assert.equal(source.includes('const ARTIFACT_ROWS_CACHE_LIMIT = 200'), true)
  assert.equal(source.includes('function readRowsCache(key) {'), true)
  assert.equal(source.includes('function writeRowsCache(key, payload) {'), true)
  assert.equal(source.includes('const cached = readRowsCache(key)'), true)
  assert.equal(source.includes('return withAbortSignal(Promise.resolve(cached), options?.signal)'), true)
  assert.equal(source.includes('writeRowsCache(key, payload)'), true)
  assert.equal(source.includes('return cloneRows(payload)'), true)
})
