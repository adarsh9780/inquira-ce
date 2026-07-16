import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api service persists API key via v1 preferences secure endpoint', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const contractPath = resolve(process.cwd(), 'src/services/contracts/v1Api.js')
  const source = readFileSync(servicePath, 'utf-8')
  const contract = readFileSync(contractPath, 'utf-8')

  assert.equal(source.includes("v1SetApiKey(apiKeyOrPayload, provider = 'openrouter')"), true)
  assert.equal(source.includes('if (apiKeyOrPayload && typeof apiKeyOrPayload === \'object\' && !Array.isArray(apiKeyOrPayload))'), true)
  assert.equal(source.includes('return v1Api.preferences.setApiKey(apiKeyOrPayload)'), true)
  assert.equal(source.includes('return v1Api.preferences.setApiKey({'), true)
  assert.equal(contract.includes('setApiKey: (payload) =>'), true)
  assert.equal(contract.includes('verifyKey: (provider, apiKey)'), true)
  assert.equal(contract.includes('/api/v1/preferences/verify-key'), true)
  assert.equal(source.includes('v1VerifyApiKey(provider, apiKey)'), true)
  assert.equal(source.includes("v1DeleteApiKey(provider = 'openrouter')"), true)
  assert.equal(source.includes('return v1Api.preferences.deleteApiKey(provider)'), true)
  assert.equal(contract.includes('/api/v1/preferences/api-key'), true)
  assert.equal(source.includes("const payload = apiKeyOrPayload && typeof apiKeyOrPayload === 'object' && !Array.isArray(apiKeyOrPayload)"), true)
  assert.equal(source.includes('const response = await this.v1SetApiKey(payload, provider)'), true)
  assert.equal(source.includes('Provider configuration saved.'), true)
})
