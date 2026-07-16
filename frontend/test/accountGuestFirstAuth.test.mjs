import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

const providerName = ['Goo', 'gle'].join('')
const signInProviderText = ['Sign in with ', providerName].join('')
const signOutProviderText = ['Sign out from ', providerName].join('')
const removedAuthConfigServiceFile = ['auth', 'ConfigService.js'].join('')
const externalAuthServiceFile = ['supa', 'baseAuthService.js'].join('')
const removedProviderAction = ['signInWith', 'Provider'].join('')
const removedProviderFlag = ['canStart', providerName, 'Login'].join('')
const removedLoopbackCommand = ['auth_start', '_loopback_listener'].join('')
const removedCallbackEvent = ['auth', ':callback'].join('')

test('auth store is local-only in CE', () => {
  const source = readSource('src/stores/authStore.js')

  assert.equal(source.includes("user_id: 'local-user'"), true)
  assert.equal(source.includes("auth_provider: 'local'"), true)
  assert.equal(source.includes('apiService.setAuthToken(\'\')'), true)
  assert.equal(source.includes(removedProviderAction), false)
  assert.equal(source.includes(removedProviderFlag), false)
  assert.equal(source.includes(removedLoopbackCommand), false)
  assert.equal(source.includes(removedCallbackEvent), false)
  assert.equal(source.includes('exchangeCodeForSession'), false)
  assert.equal(source.includes('window.__TAURI_INTERNALS__'), false)
})

test('account tab shows local workspace state without sign-in actions', () => {
  const source = readSource('src/components/modals/tabs/AccountTab.vue')

  assert.equal(source.includes('Local workspace mode active.'), true)
  assert.equal(source.includes('open-source build'), true)
  assert.equal(source.includes(signInProviderText), false)
  assert.equal(source.includes(signOutProviderText), false)
  assert.equal(source.includes('startGoogleSignIn'), false)
  assert.equal(source.includes('signOutGoogle'), false)
})

test('CE does not ship frontend Supabase auth services', () => {
  assert.equal(existsSync(resolve(process.cwd(), 'src/services/' + removedAuthConfigServiceFile)), false)
  assert.equal(existsSync(resolve(process.cwd(), 'src/services/' + externalAuthServiceFile)), false)
})
