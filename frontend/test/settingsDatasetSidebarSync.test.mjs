import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset selection from settings emits shared switch event and sidebar re-syncs catalog', () => {
  const dataTabSource = readFileSync(
    resolve(process.cwd(), 'src/components/modals/DataTab.vue'),
    'utf-8',
  )
  const sidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue'),
    'utf-8',
  )
  const unifiedSidebarSource = readFileSync(
    resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'),
    'utf-8',
  )

  assert.equal(dataTabSource.includes("new CustomEvent('dataset-switched'"), true)
  assert.equal(dataTabSource.includes('appStore.setSchemaFileId(selectedPath || selectedTableName)'), true)
  assert.equal(sidebarSource.includes("window.addEventListener('dataset-switched', handleDatasetSwitched)"), true)
  assert.equal(sidebarSource.includes('function isSelectedDataset(ds) {'), true)
  assert.equal(sidebarSource.includes('datasetTable === activeTable'), true)
  assert.equal(unifiedSidebarSource.includes("window.addEventListener('dataset-switched', handleDatasetCatalogChanged)"), true)
  assert.equal(unifiedSidebarSource.includes("window.removeEventListener('dataset-switched', handleDatasetCatalogChanged)"), true)
  assert.equal(unifiedSidebarSource.includes('void fetchDatasets()'), true)
})
