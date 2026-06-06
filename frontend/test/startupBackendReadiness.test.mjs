import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('desktop startup treats native Tauri readiness as the single service authority', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(source.includes("desktopStartup.message = 'Waiting for backend API...'"), false)
  assert.equal(source.includes('await apiService.waitForBackendReady()'), false)
  assert.equal(source.includes('if (state?.ready) {'), true)
})

test('authenticated workspace shell mounts only after account bootstrap completes', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

  assert.equal(
    source.includes('<div v-if="authStore.isAuthenticated && appBootstrap.ready" class="flex flex-col h-screen">'),
    true,
    'main workspace shell must not mount hidden child components before backend and workspace bootstrap finish',
  )
  assert.equal(
    source.includes('<div v-show="authStore.isAuthenticated && appBootstrap.ready" class="flex flex-col h-screen">'),
    false,
    'v-show keeps chat/workspace components mounted and can fire workspace API calls before startup readiness',
  )
})
