import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth modal is not hidden behind authStore.isLoading gate', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes(':is-open="isAuthUiReady && authStore.initialSessionResolved && !authStore.isAuthenticated && !appBootstrap.active"'), true)
  assert.equal(source.includes('!authStore.isAuthenticated && !authStore.isLoading'), false)
  assert.equal(source.includes('Loading Inquira'), false)
})

test('auth modal waits for backend readiness and initial session resolution before it can open', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const isAuthUiReady = ref(false)'), true)
  assert.equal(source.includes('backendStatus.active = true'), true)
  assert.equal(source.includes('await apiService.waitForBackendReady()'), true)
  assert.equal(source.includes('isAuthUiReady.value = true'), true)
  assert.equal(source.includes('authStore.initialSessionResolved'), true)
  assert.equal(source.includes('await authStore.checkAuth()'), false)
})
