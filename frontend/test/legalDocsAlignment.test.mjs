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

  assert.equal(source.includes('Supabase-backed bearer auth'), true)
  assert.equal(source.includes('Google login'), true)
  assert.equal(source.includes('These Terms do not grant rights beyond the applicable software license.'), true)
  assert.equal(source.includes('Commercial use is permitted.'), false)
})
