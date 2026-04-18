import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat model selector wires provider-aware backend fallback search', () => {
  const path = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes(':provider="appStore.llmProvider"'), true)
  assert.equal(source.includes(':backend-search="searchProviderModels"'), true)
  assert.equal(source.includes(':search-loading="appStore.providerModelSearchLoading"'), true)
  assert.equal(source.includes(':search-debounce-ms="250"'), true)
  assert.equal(source.includes('const models = await appStore.searchProviderModels(query, limit)'), true)
})

test('chat model selection still updates only main model in store', () => {
  const path = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('function handleModelChange(model) {'), true)
  assert.equal(source.includes('appStore.setSelectedModel(model)'), true)
})
