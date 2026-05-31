import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab auto-selects from the refreshed active turn artifact list', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const preferredSelection = resolvePreferredTableSelectionId(availableArtifactIds)'), true)
  assert.equal(source.includes('selectedArtifactId.value = preferredSelection'), true)
  assert.equal(source.includes('return displayArtifacts.value[0]?.artifact_id || null'), true)
  assert.equal(source.includes("const latestArtifactId = String(appStore.dataframes?.[0]?.data?.artifact_id || '').trim()"), false)
  assert.equal(source.includes('pendingAutoSelectArtifactId'), false)
})
