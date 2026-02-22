import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store local config persists only UI preferences', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('apiKey: apiKey.value'), false)
  assert.equal(source.includes('activeWorkspaceId: activeWorkspaceId.value'), false)
  assert.equal(source.includes('activeConversationId: activeConversationId.value'), false)
  assert.equal(source.includes('dataFilePath: dataFilePath.value'), false)
  assert.equal(source.includes('selectedModel: selectedModel.value'), true)
  assert.equal(source.includes('allowSchemaSampleValues: allowSchemaSampleValues.value'), true)
})
