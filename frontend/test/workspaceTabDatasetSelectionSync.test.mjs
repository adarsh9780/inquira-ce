import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('workspace tab dataset add flow syncs shared selection state and dispatches dataset-switched event', () => {
  const source = readSource('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(source.includes('function applyDatasetSelectionFromUpload(uploadResult, fallbackPath = \'\') {'), true)
  assert.equal(source.includes('appStore.setDataFilePath(resolvedPath)'), true)
  assert.equal(source.includes('appStore.setIngestedTableName(resolvedTableName)'), true)
  assert.equal(source.includes('appStore.setSchemaFileId(resolvedPath || resolvedTableName)'), true)
  assert.equal(source.includes("window.dispatchEvent(new CustomEvent('dataset-switched', {"), true)
  assert.equal(source.includes('const uploadResult = await apiService.uploadDataPath(selectedPath)'), true)
  assert.equal(source.includes('applyDatasetSelectionFromUpload(uploadResult, selectedPath)'), true)
  assert.equal(source.includes('const uploadResult = await apiService.uploadDataPath(sourcePath)'), true)
  assert.equal(source.includes('applyDatasetSelectionFromUpload(uploadResult, sourcePath)'), true)
})
