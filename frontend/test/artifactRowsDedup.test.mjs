import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native artifact rows deduplicate in-flight requests and support per-caller abort', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/api/artifacts.ts'),
    'utf8',
  )

  assert.equal(source.includes('const rowsInFlight = new Map'), true)
  assert.equal(source.includes('const sortModel = Array.isArray(options.sortModel)'), true)
  assert.equal(source.includes("const searchText = String(options.searchText || '').trim()"), true)
  assert.equal(source.includes('const key = ['), true)
  assert.equal(source.includes('JSON.stringify(sortModel)'), true)
  assert.equal(source.includes('JSON.stringify(filterModel)'), true)
  assert.equal(source.includes('rowsInFlight.get(key)'), true)
  assert.equal(source.includes('rowsInFlight.set(key, request)'), true)
  assert.equal(source.includes('rowsInFlight.delete(key)'), true)
  assert.equal(source.includes('return withAbortSignal(request, options.signal || null)'), true)
})
