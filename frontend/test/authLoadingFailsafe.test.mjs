import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth store wraps auth requests with explicit timeout fail-safe', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('const AUTH_ACTION_TIMEOUT_MS = 45000'), true)
  assert.equal(source.includes('async function withTimeout(promise, timeoutMs, message)'), true)
  assert.equal(source.includes('Promise.race(['), true)
  assert.equal(source.includes("'Authentication check timed out.'"), true)
  assert.equal(source.includes("'Provider sign-in request timed out.'"), true)
  assert.equal(source.includes("'Magic link request timed out.'"), true)
})

test('auth store does not shadow error ref inside auth action catch blocks', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('catch (error)'), false)
  assert.equal(source.includes('catch (err)'), true)
  assert.equal(source.includes('error.value = err?.message'), true)
})

test('auth store hydrates backend profile with the fresh callback bearer token', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/stores/authStore.js'),
    'utf-8',
  )

  assert.equal(source.includes('async function hydrateUserFromBackend(accessToken = \'\')'), true)
  assert.equal(source.includes('Authorization: `Bearer ${token}`'), true)
  assert.equal(source.includes('await hydrateUserFromBackend(accessToken)'), true)
})
