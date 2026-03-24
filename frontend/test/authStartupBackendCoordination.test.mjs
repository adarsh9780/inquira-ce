import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth store defers session verification until desktop backend startup is ready', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('let isBackendReady = false'), true)
  assert.equal(source.includes('let deferredSessionToken = \'\''), true)
  assert.equal(source.includes('let deferredSessionEvent = \'\''), true)
  assert.equal(source.includes("setAuthFlow('restoring_session', 'Found a saved session. Waiting for Inquira backend...')"), true)
  assert.equal(source.includes("setAuthFlow('session_ready', 'Sign-in code accepted. Waiting for Inquira backend...')"), true)
  assert.equal(source.includes('if (!isBackendReady) {'), true)
  assert.equal(source.includes('deferredSessionToken = accessToken'), true)
  assert.equal(source.includes('async function resumeDeferredSessionHydration()'), true)
  assert.equal(source.includes('await hydrateSessionFromAuthEvent(accessToken, authEvent)'), true)
})

test('app startup readiness handoff resumes deferred auth verification', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function markBackendReady() {'), true)
  assert.equal(source.includes('authStore.markBackendReady()'), true)
})
