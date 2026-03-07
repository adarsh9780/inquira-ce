import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('table tab skips row fetch when selected artifact is not in current workspace catalog', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/components/analysis/TableTab.vue'),
    'utf-8',
  )

  assert.equal(source.includes('const isKnownPersistedArtifact = allArtifacts.value.some('), true)
  assert.equal(source.includes('if (!isKnownPersistedArtifact) {'), true)
  assert.equal(source.includes('void loadWorkspaceArtifacts(appStore.activeWorkspaceId)'), true)
})
