import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth store reuses the same backend hydration for duplicate startup auth events', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('function hasHydratedCurrentToken(accessToken = \'\')'), true)
  assert.equal(source.includes('let lastHydratedAccessToken = \'\''), true)
  assert.equal(source.includes('if (hasHydratedCurrentToken(token)) return true'), true)
  assert.equal(source.includes('return activeHydrationPromise'), true)
  assert.equal(source.includes('lastHydratedAccessToken = token'), true)
})

test('auth store uses a shorter local session probe than backend profile verification', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('supabaseAuthService.getSession(),'), true)
  assert.equal(source.includes('AUTH_SESSION_TIMEOUT_MS,'), true)
  assert.equal(source.includes('apiService.v1GetCurrentUser(requestConfig),'), true)
  assert.equal(source.includes('AUTH_PROBE_TIMEOUT_MS + 1000,'), true)
})
