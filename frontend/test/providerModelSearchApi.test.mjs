import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('frontend API client exposes provider model search endpoint', () => {
  const contractPath = resolve(process.cwd(), 'src/services/contracts/v1Api.js')
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const contract = readFileSync(contractPath, 'utf-8')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(contract.includes('searchModels: ({ provider, query, limit = 25 }) =>'), true)
  assert.equal(contract.includes("axios.get('/api/v1/preferences/models/search'"), true)
  assert.equal(contract.includes('q: query,'), true)
  assert.equal(source.includes('async v1SearchProviderModels(provider, query, limit = 25) {'), true)
  assert.equal(source.includes("provider: provider,") || source.includes('provider,'), true)
  assert.equal(source.includes('query,'), true)
  assert.equal(source.includes('limit,'), true)
})
