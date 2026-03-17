import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api service exposes v1 legal terms endpoint helper', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/apiService.js'),
    'utf-8',
  )

  assert.equal(source.includes('async v1GetTermsAndConditions()'), true)
  assert.equal(source.includes("return axios.get('/api/v1/legal/terms')"), true)
})
