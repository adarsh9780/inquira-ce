import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

test('TableTab exposes promoted user revisions alongside AI artifacts', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const liveDataframeArtifacts = computed(() => {'), true)
  assert.equal(source.includes('function normalizeLiveDataframeArtifact(item, index)'), true)
  assert.equal(source.includes('return [...liveDataframeArtifacts.value, ...persistedArtifacts]'), true)
  assert.equal(source.includes("const preferredArtifactId = workspaceId ? artifactStore.getSelectedTableArtifact(workspaceId) : ''"), true)
  assert.equal(source.includes("const liveArtifact = liveDataframeArtifacts.value.find("), true)
  assert.equal(source.includes('artifactStore.promotedUserDataframes'), true)
  assert.equal(source.includes("item?.promoted ? 'revision' : 'live'"), true)
  assert.equal(source.includes('source_artifact_id'), true)
  assert.equal(source.includes('artifactApi.workspaceRows('), true)
  assert.equal(source.includes('artifactApi.listTurn('), true)
})
