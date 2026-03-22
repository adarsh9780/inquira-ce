import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('desktop supabase auth reuses shared runtime state to survive hot reloads', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/supabaseAuthService.js'),
    'utf-8',
  )

  assert.equal(source.includes("const runtimeKey = '__INQUIRA_SUPABASE_AUTH_RUNTIME__'"), true)
  assert.equal(source.includes('pendingCodes: new Set()'), true)
  assert.equal(source.includes('handledCodes: new Set()'), true)
  assert.equal(source.includes('runtime.pendingCodes.has(code) || runtime.handledCodes.has(code)'), true)
})

test('auth store retries backend hydration after auth state changes', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('async function hydrateUserFromBackendWithRetry(accessToken = \'\', maxAttempts = 3)'), true)
  assert.equal(source.includes('await sleep(400 * attempt)'), true)
  assert.equal(source.includes('await hydrateUserFromBackendWithRetry(accessToken)'), true)
})
