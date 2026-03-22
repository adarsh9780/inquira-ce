import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('authenticated app bootstrap waits for workspace selection and kernel startup before rendering the main shell', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const appBootstrap = reactive({'), true)
  assert.equal(source.includes('v-if="authStore.isAuthenticated && appBootstrap.ready"'), true)
  assert.equal(source.includes("appBootstrap.message = 'Selecting your workspace...'"), true)
  assert.equal(source.includes('await appStore.fetchWorkspaces()'), true)
  assert.equal(source.includes("appBootstrap.message = 'Starting your workspace runtime...'"), true)
  assert.equal(source.includes('await appStore.ensureWorkspaceKernelConnected(appStore.activeWorkspaceId)'), true)
  assert.equal(source.includes("appBootstrap.message = 'Loading workspace history...'"), true)
})

test('auth store exposes initial session resolution for startup gating', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('const initialSessionResolved = ref(false)'), true)
  assert.equal(source.includes('function markInitialSessionResolved(event = \'\')'), true)
  assert.equal(source.includes("if (authEvent === 'INITIAL_SESSION' || authEvent === 'SIGNED_IN' || authEvent === 'SIGNED_OUT')"), true)
  assert.equal(source.includes('markInitialSessionResolved(authEvent)'), true)
})
