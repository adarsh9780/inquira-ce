import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth flow verifies the session directly without waiting for backend health', () => {
  const path = resolve(process.cwd(), 'src/stores/authStore.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function hydrateUserFromBackend(accessToken = \'\')'), true)
  assert.equal(source.includes('apiService.waitForBackendReady'), false)
  assert.equal(source.includes('apiService.v1GetCurrentUser(requestConfig)'), true)
  assert.equal(source.includes('hydrateUserFromBackendWithRetry(accessToken)'), true)
})
