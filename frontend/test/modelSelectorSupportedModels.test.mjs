import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('model selector accepts injected model options prop', () => {
  const path = resolve(process.cwd(), 'src/components/ui/ModelSelector.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('modelOptions'), true)
  assert.equal(source.includes('maxOptionsWithoutSearch'), true)
  assert.equal(source.includes('const searchQuery = ref(\'\')'), true)
  assert.equal(source.includes('const availableModels = computed(() => {'), true)
  assert.equal(source.includes('const filteredModels = computed(() => {'), true)
  assert.equal(source.includes('return source.slice(0, limit)'), true)
  assert.equal(source.includes('placeholder="Search model"'), true)
  assert.equal(source.includes('v-model="searchQuery"'), true)
  assert.equal(source.includes('const source = Array.isArray(props.modelOptions) && props.modelOptions.length'), true)
  assert.equal(source.includes('backendSearch'), true)
  assert.equal(source.includes('provider'), true)
  assert.equal(source.includes('searchLoading'), true)
  assert.equal(source.includes('searchDebounceMs'), true)
  assert.equal(source.includes('Searching...'), true)
  assert.equal(source.includes('No models found.'), true)
  assert.equal(source.includes('class="relative w-full min-w-0"'), true)
  assert.equal(source.includes('class="inline-flex w-full min-w-0 items-center justify-between'), true)
  assert.equal(source.includes('class="min-w-0 flex-1 truncate text-left"'), true)
})

test('chat input uses the effective workspace model without duplicating model settings', () => {
  const path = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('<ModelSelector'), false)
  assert.equal(source.includes('const effectiveWorkspaceModel = computed('), true)
  assert.equal(source.includes('model: effectiveWorkspaceModel.value'), true)
  assert.equal(source.includes('resolveAnalyzeCancelTimeoutMs(effectiveWorkspaceModel.value)'), true)
})

test('app store reads available models from v1 preferences payload', () => {
  const path = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('function modelAllowedForProvider(provider, modelId)'), true)
  assert.equal(source.includes("normalizedProvider && normalizedProvider !== 'ollama' && value.includes(':cloud')"), true)
  assert.equal(source.includes('const fallbackMainModels = normalizeModelList(prefs?.provider_available_main_models, responseProvider)'), true)
  assert.equal(source.includes('mergeProviderModelOptions(llmProvider.value, [])'), true)
  assert.equal(source.includes('enabled_models:'), false)
  assert.equal(source.includes('providerModelSearchResults'), true)
  assert.equal(source.includes('async function searchProviderModels(query, limit = 25)'), true)
  assert.equal(source.includes('selectedCodingModel.value = selectedModel.value'), true)
  assert.equal(source.includes('prefs?.terminal_risk_acknowledged'), false)
  assert.equal(source.includes('terminal_risk_acknowledged: terminalConsentGranted.value'), false)
})
