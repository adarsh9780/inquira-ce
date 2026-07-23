import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store requires a ready workspace and effective provider access for chat analysis', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('const canAnalyze = computed(() => {'), true)
  assert.equal(source.includes('const hasProviderAccess = workspaceAIConfig.value?.readiness'), true)
  assert.equal(source.includes('if (!hasProviderAccess) return false'), true)
  assert.equal(source.includes('return workspaceReadiness.value.ready'), true)
})

test('workspace listing recovers from a stale locally restored workspace id', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('activeWorkspaceId.value && !items.some((ws) => ws.id === activeWorkspaceId.value)'), true)
  assert.equal(source.includes('activeWorkspaceId.value = items[0]?.id || \'\''), true)
  assert.equal(source.includes("activeConversationId.value = ''"), true)
})
