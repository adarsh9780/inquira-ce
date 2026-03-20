import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('ApiTab forwards selected model when testing provider API key', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('apiService.testGeminiApi(key, appStore.selectedModel, appStore.llmProvider)'), true)
})

test('ApiTab saves dedicated coding model preference', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('Coding Model (subagent)'), true)
  assert.equal(source.includes('selected_coding_model: appStore.selectedCodingModel'), true)
  assert.equal(source.includes('handleCodingModelChange'), true)
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

test('ApiTab shows OpenRouter account-level guidance and settings link', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('account-level models are not configured yet'), true)
  assert.equal(source.includes('openrouterAccountModelsUrl'), true)
  assert.equal(source.includes('openrouter/free'), true)
})
