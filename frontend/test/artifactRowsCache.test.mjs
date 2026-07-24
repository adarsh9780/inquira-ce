import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native artifact rows are cached by artifact, page, and query state', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/api/artifacts.ts'),
    'utf8',
  )

  assert.equal(source.includes('const rowsCache = new Map'), true)
  assert.equal(source.includes('const ROWS_CACHE_LIMIT = 200'), true)
  assert.equal(source.includes('function readCache(key: string)'), true)
  assert.equal(source.includes('function writeCache(key: string, payload: unknown)'), true)
  assert.equal(source.includes('const cached = readCache(key)'), true)
  assert.equal(source.includes('return withAbortSignal(Promise.resolve(cached), options.signal || null)'), true)
  assert.equal(source.includes('writeCache(key, payload)'), true)
  assert.equal(source.includes('return clone(payload)'), true)
})
