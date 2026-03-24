import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app mounts the auth shell whenever no authenticated user is present', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes('v-if="!startupFailure && !authStore.isAuthenticated"'), true)
  assert.equal(source.includes(':is-open="true"'), true)
  assert.equal(source.includes('authStore.isAuthModalVisible'), false)
  assert.equal(source.includes('showAuthModal'), false)
})

test('frontend startup kicks off auth initialization without polling backend readiness', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const startupFailure = ref(\'\')'), true)
  assert.equal(source.includes('const startupState = await readDesktopStartupState()'), true)
  assert.equal(source.includes('void authStore.initialize()'), true)
  assert.equal(source.includes('await apiService.waitForBackendReady()'), false)
  assert.equal(source.includes('appBootstrap.ready = true'), true)
})
