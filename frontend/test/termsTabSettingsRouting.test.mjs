import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('settings modal exposes a terms route and renders the terms tab', () => {
  const source = read('src/components/modals/SettingsModal.vue')

  assert.equal(source.includes("import TermsTab from './tabs/TermsTab.vue'"), true)
  assert.equal(source.includes('Terms &amp; Conditions'), true)
  assert.equal(source.includes("@click=\"openLeafSection('terms')\""), true)
  assert.equal(source.includes("<TermsTab :active=\"currentPanel === 'terms'\" />"), true)
  assert.equal(source.includes("if (candidate === 'legal') return 'terms'"), true)
})

test('terms tab loads markdown from the legal endpoint inside settings', () => {
  const source = read('src/components/modals/tabs/TermsTab.vue')

  assert.equal(source.includes('apiService.v1GetTermsAndConditions()'), true)
  assert.equal(source.includes("Review the current desktop usage terms inside the app."), true)
  assert.equal(source.includes("const props = defineProps({"), true)
  assert.equal(source.includes("() => props.active"), true)
  assert.equal(source.includes('Loading terms...'), true)
  assert.equal(source.includes('terms-markdown-content'), true)
})
