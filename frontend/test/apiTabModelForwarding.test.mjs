import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('ApiTab forwards selected model when testing provider API key', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('apiService.testGeminiApi(key, appStore.selectedModel, appStore.llmProvider)'), true)
})

test('ApiTab saves a single main-model selection for both chat and coding preferences', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Coding Model (subagent)'), false)
  assert.equal(source.includes('selected_coding_model: appStore.selectedModel'), true)
  assert.equal(source.includes('handleMainModelChange'), true)
  assert.equal(source.includes('MultiSelectDropdown'), false)
})

test('ApiTab is focused on provider/model configuration only', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Runner Packages'), false)
  assert.equal(source.includes('Schema Privacy'), false)
  assert.equal(source.includes('allowSchemaSampleValues'), false)
})

test('ApiTab supports provider model refresh from backend', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Refresh Models'), true)
  assert.equal(source.includes('apiService.v1RefreshProviderModels(payload)'), true)
  assert.equal(source.includes('syncProviderCatalog(appStore.llmProvider)'), true)
})

test('ApiTab requires saving the API key before provider model refresh', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.indexOf('API Provider') < source.indexOf('API Key ({{ appStore.llmProvider }})'), true)
  assert.equal(source.includes('Save Key'), true)
  assert.equal(source.includes('saveProviderApiKey'), true)
  assert.equal(source.includes('Save your API key to secure storage'), true)
  assert.equal(source.includes('Save your ${appStore.llmProvider} API key first to refresh models.'), true)
  assert.equal(source.includes(':disabled="isRefreshModelsDisabled"'), true)
  assert.equal(source.includes('inline-flex h-9 min-w-[5.5rem] items-center justify-center'), true)
  assert.equal(source.includes('v-if="hasTypedApiKey" class="flex items-center gap-2"'), true)
  assert.equal(source.includes("const hasTypedApiKey = computed(() => !!appStore.apiKey.trim())"), true)
})

test('ApiTab explains that models come from built-in defaults before refresh', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('The models shown below are built-in defaults.'), true)
  assert.equal(source.includes('Save your API key first, then refresh to load models for this provider.'), true)
})

test('ApiTab shows OpenRouter account-level guidance and settings link', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('account-level models are not configured yet'), true)
  assert.equal(source.includes('openrouterAccountModelsUrl'), true)
  assert.equal(source.includes('openrouter/free'), true)
})
