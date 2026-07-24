import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab remembers and restores pagination page per artifact selection using app store persistence', () => {
  const path = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('const pendingRestorePageByArtifact = new Map()'), true)
  assert.equal(source.includes('artifactStore.getTablePageOffset(workspaceStore.activeWorkspaceId, newId)'), true)
  assert.equal(source.includes('artifactStore.setTablePageOffset(workspaceStore.activeWorkspaceId, artifactId, normalizedQuery.pageIndex)'), true)
  assert.equal(source.includes('function restoredArtifactPage(artifactId) {'), true)
  assert.equal(source.includes('?? artifactStore.getTablePageOffset(workspaceStore.activeWorkspaceId, artifactId)'), true)
  assert.equal(source.includes('const pageIndex = restoredArtifactPage(artifactId)'), true)
  assert.equal(source.includes('tableQuery.value = createTableQuery({ pageIndex, pageSize })'), true)
  assert.equal(source.includes('await loadServerPage(artifactId, tableQuery.value)'), true)
})
