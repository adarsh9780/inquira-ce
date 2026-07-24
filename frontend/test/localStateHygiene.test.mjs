import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store does not use browser localStorage/sessionStorage', () => {
  const storePath = resolve(process.cwd(), 'src/composables/useSessionSnapshot.ts')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('localStorage'), false)
  assert.equal(source.includes('sessionStorage'), false)
})
