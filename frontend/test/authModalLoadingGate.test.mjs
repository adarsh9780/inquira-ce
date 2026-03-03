import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth modal is not hidden behind authStore.isLoading gate', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/App.vue'),
    'utf-8',
  )

  assert.equal(source.includes(':is-open="!authStore.isAuthenticated"'), true)
  assert.equal(source.includes('!authStore.isAuthenticated && !authStore.isLoading'), false)
  assert.equal(source.includes('Loading Inquira'), false)
})
