import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab recovers when selected artifact rows endpoint returns 404', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('function isMissingArtifactRowsError(error)'), true)
  assert.equal(source.includes("message.includes('Artifact rows not found')"), true)
  assert.equal(source.includes('async function recoverFromMissingArtifact(artifactId)'), true)
  assert.equal(source.includes('await loadWorkspaceArtifacts(appStore.activeWorkspaceId)'), true)
  assert.equal(source.includes('selectedArtifactId.value = fallbackId'), true)
  assert.equal(source.includes('Selected table was removed. Refreshing table list...'), true)
})
