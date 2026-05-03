import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar uses a minimal workspace dropdown above the explorer sections', () => {
  const unifiedPath = resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue')
  const workspacesPath = resolve(process.cwd(), 'src/components/layout/sidebar/SidebarWorkspaces.vue')
  const unifiedSource = readFileSync(unifiedPath, 'utf-8')
  const workspacesSource = readFileSync(workspacesPath, 'utf-8')

  assert.equal(workspacesSource.includes('ListboxButton'), true)
  assert.equal(workspacesSource.includes('ListboxOptions'), true)
  assert.equal(workspacesSource.includes('ChevronUpDownIcon'), true)
  assert.equal(workspacesSource.includes('appStore.workspaces'), true)
  assert.equal(unifiedSource.includes('Workspace explorer'), false)
  assert.equal(unifiedSource.includes('workspaceFilename'), false)
  assert.equal(unifiedSource.includes('duckdb_path'), false)
  assert.equal(unifiedSource.includes('refreshWorkspaceDatasetSummary'), true)
  assert.equal(unifiedSource.includes("apiService.v1ListDatasets(workspaceId)"), true)
  assert.equal(unifiedSource.includes("count === 1 ? '1 dataset' : `${count} datasets`"), true)
  assert.equal(unifiedSource.includes("const usage = Number.isFinite(bytes) ? `${formatStorage(bytes)} used` : 'storage used'"), true)
})
