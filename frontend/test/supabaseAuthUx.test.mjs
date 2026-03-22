import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth screen focuses on Google sign-in and keeps other providers disabled as coming soon', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/modals/AuthModal.vue'),
    'utf-8',
  )

  assert.equal(source.includes('Sign in with Google'), true)
  assert.equal(source.includes('Microsoft'), true)
  assert.equal(source.includes('GitHub'), true)
  assert.equal(source.includes('Coming soon'), true)
  assert.equal(source.includes('Email Magic Link'), false)
  assert.equal(source.includes('Send Magic Link'), false)
  assert.equal(source.includes('Username'), false)
  assert.equal(source.includes('Create Account'), false)
  assert.equal(source.includes('Welcome back. Sign in with Google to access your workspace.'), true)
})

test('account tab routes users to browser-managed account controls', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/modals/AccountTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('Manage Account'), true)
  assert.equal(source.includes('Password changes, account recovery'), true)
  assert.equal(source.includes('Change Password'), false)
  assert.equal(source.includes('Delete Account'), false)
  assert.equal(source.includes('openExternalUrl(authStore.manageAccountUrl)'), true)
})
