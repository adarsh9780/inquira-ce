import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('sidebar opens the standalone terms modal', () => {
  const source = read('src/components/layout/UnifiedSidebar.vue')

  assert.equal(source.includes("import TermsModal from '../modals/TermsModal.vue'"), true)
  assert.equal(source.includes('<TermsModal'), true)
  assert.equal(source.includes('@click="openTermsModal"'), true)
})

test('terms modal loads markdown from the legal endpoint', () => {
  const source = read('src/components/modals/TermsModal.vue')

  assert.equal(source.includes('apiService.v1GetTermsAndConditions()'), true)
  assert.equal(source.includes("const props = defineProps({"), true)
  assert.equal(source.includes("() => props.isOpen"), true)
  assert.equal(source.includes('Loading terms...'), true)
  assert.equal(source.includes('terms-markdown-content'), true)
})
