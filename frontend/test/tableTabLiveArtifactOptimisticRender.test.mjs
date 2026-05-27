import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab exposes live persisted dataframe artifacts before artifact catalog refresh catches up', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const livePersistedArtifactSummaries = computed(() => {'), true)
  assert.equal(source.includes('const optimisticPersistedArtifacts = livePersistedArtifactSummaries.value.filter'), true)
  assert.equal(source.includes('return [...persistedArtifacts, ...optimisticPersistedArtifacts, ...memoryArtifacts.value]'), true)
  assert.equal(source.includes("entry?.source === 'artifact' && String(entry?.artifact_id || '').trim() === String(newId || '').trim()"), true)
})
