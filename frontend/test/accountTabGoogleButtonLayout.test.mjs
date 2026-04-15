import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('settings account tab keeps Google auth controls and local-user fallback messaging', () => {
  const source = readSource('src/components/modals/tabs/AccountTab.vue')

  assert.equal(source.includes('Display name'), false)
  assert.equal(source.includes('v{{ version }}'), false)
  assert.equal(source.includes('v-if="authStore.isGuest"'), true)
  assert.equal(source.includes('Sign in with Google'), true)
  assert.equal(source.includes('Sign out from Google'), true)
  assert.equal(source.includes('Google account added already.'), true)
  assert.equal(source.includes('Sign out from Google converts account back Local User mode.'), true)
  assert.equal(source.includes('toast.success(\'Google account added\''), true)
  assert.equal(source.includes('toast.success(\'Signed out from Google\''), true)
  assert.equal(source.includes("@click=\"startGoogleSignIn\""), true)
  assert.equal(source.includes("@click=\"signOutGoogle\""), true)
  assert.equal(source.includes("authStore.signInWithProvider('google')"), true)
  assert.equal(source.includes('authStore.logout()'), true)
  assert.equal(source.includes('fill="#4285F4"'), true)
  assert.equal(source.includes('fill="#34A853"'), true)
  assert.equal(source.includes('fill="#FBBC05"'), true)
  assert.equal(source.includes('fill="#EA4335"'), true)

  assert.equal(source.includes('Theme'), false)
  assert.equal(source.includes('Default LLM provider'), false)
  assert.equal(source.includes('Local workspace data'), false)
  assert.equal(source.includes('Clear all conversation history'), false)
})
