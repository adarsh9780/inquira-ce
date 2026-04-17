import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('LLM settings tab shows provider-specific API key creation links', () => {
  const source = read('src/components/modals/tabs/LLMSettingsTab.vue')

  assert.equal(source.includes("const providerApiKeyPortal = computed(() => {"), true)
  assert.equal(source.includes("if (provider.value === 'openai') return 'https://platform.openai.com/api-keys'"), true)
  assert.equal(source.includes("if (provider.value === 'openrouter') return 'https://openrouter.ai/keys'"), true)
  assert.equal(source.includes('v-if="providerApiKeyPortal"'), true)
  assert.equal(source.includes('@click.prevent="openProviderApiKeyPortal"'), true)
  assert.equal(source.includes('Create {{ providerDisplayName }} API key'), true)
  assert.equal(source.includes('openExternalUrl(url)'), true)
})
