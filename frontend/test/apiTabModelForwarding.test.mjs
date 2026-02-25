import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('ApiTab forwards selected model when testing provider API key', () => {
  const path = resolve(process.cwd(), 'src/components/modals/ApiTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('apiService.testGeminiApi(key, appStore.selectedModel)'), true)
})
