import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('auth store is guest-first and wires Google OAuth through the desktop callback bridge', () => {
  const source = readSource('src/stores/authStore.js')

  assert.equal(source.includes("user_id: 'local-user'"), true)
  assert.equal(source.includes('const isGuest = computed(() => Boolean(user.value?.is_guest !== false))'), true)
  assert.equal(source.includes('apiService.setAuthToken(nextToken)'), true)
  assert.equal(source.includes("await invoke('auth_start_loopback_listener')") || source.includes("const loopback = await invoke('auth_start_loopback_listener')"), true)
  assert.equal(source.includes("listen('auth:callback'"), true)
  assert.equal(source.includes('exchangeCodeForSession(code)'), true)
  assert.equal(source.includes("signInWithProvider(provider = 'google')"), true)
  assert.equal(source.includes("window.__TAURI_INTERNALS__"), true)
})

test('account tab shows Google login for guests and manage account for signed-in users', () => {
  const source = readSource('src/components/modals/AccountTab.vue')

  assert.equal(source.includes("v-if=\"authStore.isGuest\""), true)
  assert.equal(source.includes('Continue with Google'), true)
  assert.equal(source.includes('Manage Account'), true)
  assert.equal(source.includes('Sign Out'), true)
  assert.equal(source.includes('startGoogleSignIn'), true)
  assert.equal(source.includes('authStore.manageAccountUrl'), true)
  assert.equal(source.includes('You are currently using the free local mode.'), true)
})

test('auth config loads from the backend first and falls back to env values', () => {
  const source = readSource('src/services/authConfigService.js')

  assert.equal(source.includes('v1Api.auth.config()'), true)
  assert.equal(source.includes('return envConfig()'), true)
  assert.equal(source.includes('Falling back to env-based auth config'), true)
})
