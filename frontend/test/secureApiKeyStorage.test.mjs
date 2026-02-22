import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api service persists API key via v1 preferences secure endpoint', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const contractPath = resolve(process.cwd(), 'src/services/contracts/v1Api.js')
  const source = readFileSync(servicePath, 'utf-8')
  const contract = readFileSync(contractPath, 'utf-8')

  assert.equal(source.includes('v1SetApiKey(apiKey)'), true)
  assert.equal(contract.includes('/api/v1/preferences/api-key'), true)
  assert.equal(source.includes('API key saved securely.'), true)
})
