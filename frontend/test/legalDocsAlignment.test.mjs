import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const publicTermsPath = path.resolve('public/terms-and-conditions.html')

test('CE edition does not ship AuthModal (auth removed)', () => {
  const authModalPath = path.resolve('src/components/modals/AuthModal.vue')
  assert.equal(fs.existsSync(authModalPath), false, 'AuthModal.vue should not exist in CE')
})

test('bundled desktop terms reflect current auth and license boundaries', () => {
  const source = fs.readFileSync(publicTermsPath, 'utf8')

  assert.equal(source.includes('without account sign-in'), true)
  assert.equal(source.includes('Account sign-in, cloud sync, hosted account management, and paid plan gates are not included'), true)
  assert.equal(source.includes('-backed bearer auth'), false)
  assert.equal(source.includes('login'), false)
  assert.equal(source.includes('These Terms do not grant rights beyond the applicable software license.'), true)
  assert.equal(source.includes('Execution is not sandboxed.'), true)
  assert.equal(source.includes('policy checks reduce some risks but are not a security boundary.'), true)
  assert.equal(source.includes('Commercial use is permitted.'), false)
})
