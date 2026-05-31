import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab shows selected artifact row failures instead of recovering to another source', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function isMissingArtifactRowsError(error)'), false)
  assert.equal(source.includes("message.includes('Artifact rows not found')"), false)
  assert.equal(source.includes('async function recoverFromMissingArtifact(artifactId)'), false)
  assert.equal(source.includes('await loadWorkspaceArtifacts(appStore.activeWorkspaceId)'), false)
  assert.equal(source.includes('selectedArtifactId.value = fallbackId'), false)
  assert.equal(source.includes('Selected table was removed. Refreshing table list...'), false)
  assert.equal(source.includes("tableError.value = error?.message || 'Failed to load table data.'"), true)
})
