import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('settings account tab stays local-only in CE', () => {
  const source = readSource('src/components/modals/tabs/AccountTab.vue')
  const providerName = ['Goo', 'gle'].join('')
  const removedProviderAction = ['signInWith', 'Provider'].join('')

  assert.equal(source.includes('Display name'), false)
  assert.equal(source.includes('v{{ version }}'), false)
  assert.equal(source.includes('Local workspace mode active.'), true)
  assert.equal(source.includes('Inquira CE stores your workspace locally.'), true)
  assert.equal(source.includes('Account sign-in and cloud sync are not included'), true)
  assert.equal(source.includes(`Sign in with ${providerName}`), false)
  assert.equal(source.includes(`Sign out from ${providerName}`), false)
  assert.equal(source.includes(`${providerName} account linked.`), false)
  assert.equal(source.includes('toast.success'), false)
  assert.equal(source.includes('@click='), false)
  assert.equal(source.includes(removedProviderAction), false)
  assert.equal(source.includes('fill="#4285F4"'), false)

  assert.equal(source.includes('Theme'), false)
  assert.equal(source.includes('<HeaderDropdown'), false)
  assert.equal(source.includes('Default LLM provider'), false)
  assert.equal(source.includes('Local workspace data'), false)
  assert.equal(source.includes('Clear all conversation history'), false)
})
