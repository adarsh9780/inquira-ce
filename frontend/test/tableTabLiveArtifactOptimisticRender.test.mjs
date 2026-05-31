import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab does not expose optimistic live dataframe artifacts before turn catalog refresh', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const livePersistedArtifactSummaries = computed(() => {'), false)
  assert.equal(source.includes('const optimisticPersistedArtifacts = livePersistedArtifactSummaries.value.filter'), false)
  assert.equal(source.includes('return [...persistedArtifacts, ...optimisticPersistedArtifacts, ...memoryArtifacts.value]'), false)
  assert.equal(source.includes("entry?.source === 'artifact' && String(entry?.artifact_id || '').trim() === String(newId || '').trim()"), false)
  assert.equal(source.includes('apiService.v1ListTurnArtifacts('), true)
})
