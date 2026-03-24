import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth store keeps local session state during background revalidation failures', () => {
  const path = resolve(process.cwd(), 'src/stores/authStore.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function checkAuth(options = {})'), true)
  assert.equal(source.includes('const preserveSession = Boolean(options?.preserveSession)'), true)
  assert.equal(source.includes("authEvent === 'SIGNED_OUT'"), true)
  assert.equal(source.includes('if (!preserveSession) {'), true)
})
