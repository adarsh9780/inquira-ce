import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('TableTab remembers and restores pagination page per artifact selection using app store persistence', () => {
  const path = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(path, 'utf-8')

  assert.equal(source.includes('const pendingRestorePageByArtifact = new Map()'), true)
  assert.equal(source.includes('appStore.getTablePageOffset(appStore.activeWorkspaceId, newId)'), true)
  assert.equal(source.includes('appStore.setTablePageOffset(appStore.activeWorkspaceId, aid, page)'), true)
  assert.equal(source.includes('function restoreArtifactPage(artifactId) {'), true)
  assert.equal(source.includes('?? appStore.getTablePageOffset(appStore.activeWorkspaceId, artifactId)'), true)
  assert.equal(source.includes('if (page === 0) return'), true)
  assert.equal(source.includes('gridApi.paginationGoToPage?.(targetPage)'), true)
  assert.equal(source.includes('restoreArtifactPage(artifactId)'), true)
})
