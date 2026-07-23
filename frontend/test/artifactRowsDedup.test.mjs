import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('native artifact rows deduplicate in-flight requests and support per-caller abort', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/apiService.js'),
    'utf8',
  )

  assert.equal(source.includes('const artifactRowsInFlight = new Map()'), true)
  assert.equal(source.includes('const sortModel = Array.isArray(options?.sortModel)'), true)
  assert.equal(source.includes("const searchText = String(options?.searchText || '').trim()"), true)
  assert.equal(source.includes('const key = ['), true)
  assert.equal(source.includes('JSON.stringify(sortModel)'), true)
  assert.equal(source.includes('JSON.stringify(filterModel)'), true)
  assert.equal(source.includes('artifactRowsInFlight.get(key)'), true)
  assert.equal(source.includes('artifactRowsInFlight.set(key, inFlight)'), true)
  assert.equal(source.includes('artifactRowsInFlight.delete(key)'), true)
  assert.equal(source.includes('return withAbortSignal(inFlight, options?.signal)'), true)
})
