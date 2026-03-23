import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('auth progress keeps one shell mounted and updates headline copy instead of remounting the full screen', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/modals/AuthModal.vue'),
    'utf-8',
  )

  assert.equal(source.includes('mode="out-in"'), false)
  assert.equal(source.includes(":key=\"showProgressScreen ? 'progress' : 'signin'\""), false)
  assert.equal(source.includes('const heroTitle = computed(() => {'), true)
  assert.equal(source.includes('const heroDescription = computed(() => {'), true)
  assert.equal(source.includes('const activeBrandBullets = computed(() => (showProgressScreen.value ? progressBullets : brandBullets))'), true)
  assert.equal(source.includes('One steady screen'), true)
  assert.equal(source.includes('This screen stays in place while Inquira verifies your session and restores your workspace.'), true)
})
