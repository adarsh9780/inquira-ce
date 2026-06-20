import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab exposes manual run dataframe artifacts before turn catalog refresh', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const liveDataframeArtifacts = computed(() => {'), true)
  assert.equal(source.includes('function normalizeLiveDataframeArtifact(item, index)'), true)
  assert.equal(source.includes('return [...liveDataframeArtifacts.value, ...persistedArtifacts]'), true)
  assert.equal(source.includes("const preferredArtifactId = workspaceId ? appStore.getSelectedTableArtifact(workspaceId) : ''"), true)
  assert.equal(source.includes("const liveArtifact = liveDataframeArtifacts.value.find("), true)
  assert.equal(source.includes("source: 'live'"), true)
  assert.equal(source.includes('apiService.v1ListTurnArtifacts('), true)
})
