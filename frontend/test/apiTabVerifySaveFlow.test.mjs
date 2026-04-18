import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('API tab verify-save flow applies backend preferences response', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function verifyAndSaveProviderConfig()'), true)
  assert.equal(source.includes("message.value = 'Key saved. Model refresh failed. Use Refresh Models to retry.'"), true)
  assert.equal(source.includes('const response = await apiService.setApiKeySettings(payload, appStore.llmProvider)'), true)
  assert.equal(source.includes('appStore.applyPreferencesResponse(response)'), true)
  assert.equal(source.includes('response?.warning'), true)
  assert.equal(source.includes('refreshProviderModels'), true)
  assert.equal(source.includes(':backend-search="searchProviderModels"'), true)
  assert.equal(source.includes('syncProviderCatalog'), false)
  assert.equal(source.includes('Verify &amp; Save'), true)
  assert.equal(source.includes('v-model="ollamaBaseUrl"'), true)
})
