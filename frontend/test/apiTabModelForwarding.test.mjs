import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('ApiTab verify-save payload forwards selected main model for coding model', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('selected_coding_model: appStore.selectedModel'), true)
  assert.equal(source.includes('selected_model: appStore.selectedModel'), true)
  assert.equal(source.includes('selected_lite_model: appStore.selectedLiteModel'), true)
})

test('ApiTab refresh flow relies on backend preferences response instead of local catalog rewriting', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('apiService.v1RefreshProviderModels(payload)'), true)
  assert.equal(source.includes('appStore.applyPreferencesResponse(response)'), true)
  assert.equal(source.includes('syncProviderCatalog(appStore.llmProvider)'), false)
})

test('ApiTab exposes Verify & Save action and hides legacy Save Key/Test key flow', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Verify &amp; Save'), true)
  assert.equal(source.includes('saveProviderApiKey'), false)
  assert.equal(source.includes('testApiKey'), false)
  assert.equal(source.includes('Save Key'), false)
})

test('ApiTab uses shared searchable ModelSelector for main model and omits enabled_models updates', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('<ModelSelector'), true)
  assert.equal(source.includes(':provider="appStore.llmProvider"'), true)
  assert.equal(source.includes(':search-loading="appStore.providerModelSearchLoading"'), true)
  assert.equal(source.includes('enabled_models:'), false)
})

test('ApiTab captures Ollama base URL and verifies provider config in one flow', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Ollama Base URL'), true)
  assert.equal(source.includes('v-model="ollamaBaseUrl"'), true)
  assert.equal(source.includes('payload.base_url = String(ollamaBaseUrl.value || \'\').trim() || \'http://localhost:11434\''), true)
  assert.equal(source.includes('async function verifyAndSaveProviderConfig()'), true)
})
