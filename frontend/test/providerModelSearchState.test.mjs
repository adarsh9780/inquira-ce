import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store keeps provider-scoped search cache and merged model ordering', () => {
  const path = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('const providerModelSearchResults = ref({})'), true)
  assert.equal(source.includes('const providerModelSearchLoading = ref(false)'), true)
  assert.equal(source.includes("const providerModelSearchQuery = ref('')"), true)
  assert.equal(source.includes('function providerModelSearchCacheKey(provider, query)'), true)
  assert.equal(source.includes('function mergeProviderModelOptions(provider, results = [])'), true)
  assert.equal(source.includes('if (selected && modelAllowedForProvider(normalizedProvider, selected))'), true)
  assert.equal(source.includes('merged.push(...displayModels)'), true)
  assert.equal(source.includes('merged.push(...searchModels)'), true)
  assert.equal(source.includes('availableModels.value = normalizeModelList(merged, normalizedProvider)'), true)
})

test('app store clears stale search cache on provider change and preferences apply', () => {
  const path = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('function clearProviderModelSearchState()'), true)
  assert.equal(source.includes('providerModelSearchResults.value = {}'), true)
  assert.equal(source.includes('setLlmProvider(provider) {'), true)
  assert.equal(source.includes('clearProviderModelSearchState()'), true)
  assert.equal(source.includes('const providerChanged = previousProvider !== llmProvider.value'), true)
  assert.equal(source.includes('mergeProviderModelOptions(llmProvider.value, [])'), true)
})

test('searchProviderModels enforces provider-local search and query threshold', () => {
  const path = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function searchProviderModels(query, limit = 25)'), true)
  assert.equal(source.includes('if (normalizedQuery.length < 3)'), true)
  assert.equal(source.includes('const response = await apiService.v1SearchProviderModels(provider, normalizedQuery, limit)'), true)
  assert.equal(source.includes('const searchModels = normalizeSearchModelIds(response?.models, provider)'), true)
  assert.equal(source.includes('if (requestToken !== providerModelSearchToken)'), true)
})
