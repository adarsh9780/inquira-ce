import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const authModalPath = path.resolve('src/components/modals/AuthModal.vue')
const publicTermsPath = path.resolve('public/terms-and-conditions.html')

test('auth modal opens published docs site terms instead of a repository blob', () => {
  const source = fs.readFileSync(authModalPath, 'utf8')

  assert.equal(source.includes("https://docs.inquiraai.com/terms-of-service"), true)
  assert.equal(source.includes('github.com/adarsh9780/inquira-ce/blob/main/frontend/public/terms-and-conditions.html'), false)
})

test('bundled desktop terms reflect current auth and license boundaries', () => {
  const source = fs.readFileSync(publicTermsPath, 'utf8')

  assert.equal(source.includes('Supabase-backed bearer auth'), true)
  assert.equal(source.includes('Google login'), true)
  assert.equal(source.includes('These Terms do not grant rights beyond the applicable software license.'), true)
  assert.equal(source.includes('Commercial use is permitted.'), false)
})
