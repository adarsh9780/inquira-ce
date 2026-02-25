import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('app store requires active workspace and API key for chat analysis', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('const canAnalyze = computed(() => {'), true)
  assert.equal(source.includes('if (!apiKeyConfigured.value) return false'), true)
  assert.equal(source.includes('return hasWorkspace.value'), true)
})

test('user preferences recover from stale active workspace ids', () => {
  const storePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(storePath, 'utf-8')

  assert.equal(source.includes('Preferences may point to deleted/stale workspace IDs.'), true)
  assert.equal(source.includes('!workspaces.value.some((ws) => ws.id === activeWorkspaceId.value)'), true)
  assert.equal(source.includes('activeWorkspaceId.value = active?.id || \'\''), true)
})
