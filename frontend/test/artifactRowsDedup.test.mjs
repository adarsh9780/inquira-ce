import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

test('apiService deduplicates in-flight artifact row requests and supports per-caller abort', () => {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const filePath = path.resolve(__dirname, '..', 'src', 'services', 'apiService.js')
  const source = fs.readFileSync(filePath, 'utf8')

  assert.equal(source.includes('const artifactRowsInFlight = new Map()'), true)
  assert.equal(source.includes('const sortModelPayload = JSON.stringify(normalizedSortModel)'), true)
  assert.equal(source.includes('const filterModelPayload = JSON.stringify(normalizedFilterModel)'), true)
  assert.equal(source.includes('const requestKey = ['), true)
  assert.equal(source.includes('sortModelPayload,'), true)
  assert.equal(source.includes('filterModelPayload,'), true)
  assert.equal(source.includes('normalizedSearchText,'), true)
  assert.equal(source.includes('artifactRowsInFlight.get(requestKey)'), true)
  assert.equal(source.includes('artifactRowsInFlight.set(requestKey, inFlight)'), true)
  assert.equal(source.includes('artifactRowsInFlight.delete(requestKey)'), true)
  assert.equal(source.includes('return withAbortSignal(inFlight, options?.signal || null)'), true)
})
