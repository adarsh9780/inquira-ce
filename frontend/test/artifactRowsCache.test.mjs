import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

test('apiService caches artifact row responses by workspace, artifact, page, and query state', () => {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const filePath = path.resolve(__dirname, '..', 'src', 'services', 'apiService.js')
  const source = fs.readFileSync(filePath, 'utf8')

  assert.equal(source.includes('const artifactRowsCache = new Map()'), true)
  assert.equal(source.includes('const ARTIFACT_ROWS_CACHE_LIMIT = 200'), true)
  assert.equal(source.includes('function readArtifactRowsCache(requestKey) {'), true)
  assert.equal(source.includes('function writeArtifactRowsCache(requestKey, payload) {'), true)
  assert.equal(source.includes('const cached = readArtifactRowsCache(requestKey)'), true)
  assert.equal(source.includes('return withAbortSignal(Promise.resolve(cached), options?.signal || null)'), true)
  assert.equal(source.includes('writeArtifactRowsCache(requestKey, payload)'), true)
  assert.equal(source.includes('return cloneArtifactRowsPayload(payload)'), true)
})
