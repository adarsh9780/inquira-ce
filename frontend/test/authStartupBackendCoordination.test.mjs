import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth store initializes the auth shell by checking and restoring a saved session once', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('let activeInitializePromise = null'), true)
  assert.equal(source.includes('async function initialize()'), true)
  assert.equal(source.includes("setAuthFlow('checking_session', 'Checking for a saved session...')"), true)
  assert.equal(source.includes('return await restoreSavedSession(accessToken)'), true)
  assert.equal(source.includes('let isBackendReady = false'), false)
  assert.equal(source.includes('let deferredSessionToken = \'\''), false)
})

test('app shell reads native startup state once before initializing auth', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes('async function readDesktopStartupState()'), true)
  assert.equal(source.includes("invoke('get_startup_state')"), true)
  assert.equal(source.includes('void authStore.initialize()'), true)
  assert.equal(source.includes('markBackendReady'), false)
})
