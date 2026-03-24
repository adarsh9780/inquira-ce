import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth modal visibility is driven by explicit auth store state', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes(':is-open="authStore.isAuthModalVisible"'), true)
  assert.equal(source.includes('@close="authStore.hideAuthModal"'), true)
  assert.equal(source.includes('showAuthModal: () => { isAuthModalVisible.value = true }'), false)
  assert.equal(source.includes('!authStore.isAuthenticated && !authStore.isLoading'), false)
  assert.equal(source.includes('isAuthUiReady && authStore.initialSessionResolved'), false)
})

test('startup gating still waits for backend readiness before the app shell becomes ready', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const isAuthUiReady = ref(false)'), true)
  assert.equal(source.includes('backendStatus.active = true'), true)
  assert.equal(source.includes('await apiService.waitForBackendReady()'), true)
  assert.equal(source.includes('isAuthUiReady.value = true'), true)
  assert.equal(source.includes('appBootstrap.ready = true'), true)
  assert.equal(source.includes('authStore.isAuthModalVisible'), true)
})
