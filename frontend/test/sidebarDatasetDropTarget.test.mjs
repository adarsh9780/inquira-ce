import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('sidebar datasets supports drag and drop ingest into the active workspace', () => {
  const componentPath = resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue')
  const source = readFileSync(componentPath, 'utf-8')

  assert.equal(source.includes('@drop.prevent="handleDatasetDrop"'), true)
  assert.equal(source.includes('Drop CSV, Parquet, Excel, JSON, or TSV files'), true)
  assert.equal(source.includes('getDroppedDatasetPaths'), true)
  assert.equal(source.includes('await appStore.startDatasetIngestion(droppedPaths'), true)
  assert.equal(source.includes('apiService.uploadDataPath(path)'), false)
  assert.equal(source.includes('toast.info('), true)
})
