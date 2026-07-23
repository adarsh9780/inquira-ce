import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('chat composer delegates model management to workspace settings', () => {
  const path = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('<ModelSelector'), false)
  assert.equal(source.includes(':backend-search="searchProviderModels"'), false)
  assert.equal(source.includes('apiService.v1SearchProviderModels('), false)
  assert.equal(source.includes('const effectiveWorkspaceModel = computed('), true)
})

test('chat requests continue to use the effective workspace model', () => {
  const path = resolve(process.cwd(), 'src/components/chat/ChatInput.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('async function handleModelChange(model) {'), false)
  assert.equal(source.includes('model: effectiveWorkspaceModel.value'), true)
  assert.equal(source.includes('resolveAnalyzeCancelTimeoutMs(effectiveWorkspaceModel.value)'), true)
})
