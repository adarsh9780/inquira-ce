import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth modal offers provider sign-in and magic link instead of local username/password auth', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/modals/AuthModal.vue'),
    'utf-8',
  )

  assert.equal(source.includes('Continue with Google'), true)
  assert.equal(source.includes('Continue with Microsoft'), true)
  assert.equal(source.includes('Continue with GitHub'), true)
  assert.equal(source.includes('Email Magic Link'), true)
  assert.equal(source.includes('Send Magic Link'), true)
  assert.equal(source.includes('Username'), false)
  assert.equal(source.includes('Create Account'), false)
  assert.equal(source.includes('Sign In To Inquira'), true)
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
