import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset selection from workspace settings emits shared switch event and the dataset surface re-syncs', () => {
  const workspaceTabSource = readFileSync(resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'), 'utf-8')
  const sidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue'), 'utf-8')
  const unifiedSidebarSource = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(workspaceTabSource.includes("new CustomEvent('dataset-switched'"), true)
  assert.equal(workspaceTabSource.includes('appStore.setSchemaFileId(resolvedPath || resolvedTableName)'), true)
  assert.equal(sidebarSource.includes("window.addEventListener('dataset-switched', handleDatasetSwitched)"), true)
  assert.equal(sidebarSource.includes('function isSelectedDataset(ds) {'), true)
  assert.equal(sidebarSource.includes('datasetTable === activeTable'), true)
  assert.equal(unifiedSidebarSource.includes("window.addEventListener('dataset-switched', handleDatasetsChanged)"), false)
  assert.equal(unifiedSidebarSource.includes('refreshWorkspaceDatasetSummary'), false)
  assert.equal(unifiedSidebarSource.includes('visibleConversationsForSidebar(workspace)'), true)
})
