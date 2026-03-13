import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('axios response interceptor forwards backend detail into the thrown error message', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')

  assert.equal(source.includes("import { extractApiErrorMessage } from '../utils/apiError'"), true)
  assert.equal(source.includes('error.message = extractApiErrorMessage('), true)
  assert.equal(
    source.includes("error.message || `Request failed with status ${error.response.status}`"),
    true,
  )
})
