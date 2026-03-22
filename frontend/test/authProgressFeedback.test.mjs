import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth screen renders a dedicated progress experience for reconnect and login completion', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/modals/AuthModal.vue'),
    'utf-8',
  )

  assert.equal(source.includes("v-if=\"showProgressScreen\""), true)
  assert.equal(source.includes('Browser step completed'), true)
  assert.equal(source.includes('Exchanging sign-in code'), true)
  assert.equal(source.includes('Restoring saved session'), true)
  assert.equal(source.includes('Verifying session'), true)
  assert.equal(source.includes('Loading your account'), true)
  assert.equal(source.includes('auth-typewriter'), true)
  assert.equal(source.includes('Continue with Google'), true)
})

test('auth store tracks stepwise login progress and waits for backend readiness', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes("window.addEventListener('inquira:auth-progress'"), true)
  assert.equal(source.includes("if (authEvent === 'INITIAL_SESSION')"), true)
  assert.equal(source.includes("setAuthFlow('restoring_session', 'Found a saved session. Reconnecting to Inquira...')"), true)
  assert.equal(source.includes("setAuthFlow('browser_complete', 'Browser sign-in finished. Completing sign-in in the app...')"), true)
  assert.equal(source.includes("setAuthFlow('verifying_session', 'Browser sign-in finished. Verifying your session with Inquira...')"), true)
  assert.equal(source.includes('await apiService.waitForBackendReady(AUTH_PROBE_TIMEOUT_MS)'), true)
})

test('api service exposes backend readiness waiting for auth verification', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/apiService.js'),
    'utf-8',
  )

  assert.equal(source.includes('async function waitForApiBaseReady(timeoutMs = 5000)'), true)
  assert.equal(source.includes('async function waitForBackendReady(timeoutMs = 30000)'), true)
  assert.equal(source.includes("/health"), true)
  assert.equal(source.includes('waitForBackendReady,'), true)
})
