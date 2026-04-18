import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('API tab verify-save flow applies backend preferences response', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function saveProviderApiKey()'), true)
  assert.equal(source.includes('const response = await apiService.setApiKeySettings(key, appStore.llmProvider)'), true)
  assert.equal(source.includes('appStore.applyPreferencesResponse(response)'), true)
  assert.equal(source.includes('response?.warning'), true)
  assert.equal(source.includes('refreshProviderModels'), true)
  assert.equal(source.includes(':backend-search="searchProviderModels"'), true)
  assert.equal(source.includes('appStore.providerMainModels = [...mainModels]'), true)
  assert.equal(source.includes('appStore.availableModels = [...mainModels]'), true)
})
