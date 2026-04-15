import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('llm settings tab resets key state and reloads preferences when auth user changes', () => {
  const source = readSource('src/components/modals/tabs/LLMSettingsTab.vue')

  assert.equal(source.includes("import { useAuthStore } from '../../../stores/authStore'"), true)
  assert.equal(source.includes('watch('), true)
  assert.equal(source.includes('() => authStore.userId'), true)
  assert.equal(source.includes('resetForAuthBoundary()'), true)
  assert.equal(source.includes('await loadPreferences(null, false)'), true)
})

test('llm config composable exposes auth-boundary reset for provider/key presence caches', () => {
  const source = readSource('src/composables/useLLMConfig.js')

  assert.equal(source.includes('function resetForAuthBoundary()'), true)
  assert.equal(source.includes('apiKeyPresenceByProvider.value = {}'), true)
  assert.equal(source.includes('selectedProviderApiKeyPresent.value = false'), true)
  assert.equal(source.includes('providerCatalogs.value = {}'), true)
  assert.equal(source.includes('resetForAuthBoundary,'), true)
})
