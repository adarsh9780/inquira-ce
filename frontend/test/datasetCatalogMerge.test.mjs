import test from 'node:test'
import assert from 'node:assert/strict'

import { mergeDatasetSources } from '../src/utils/datasetCatalogMerge.js'

test('mergeDatasetSources includes runtime table when backend catalog is empty', () => {
  const merged = mergeDatasetSources({
    catalogDatasets: [],
    runtimeTables: ['ball_by_ball_ipl'],
    currentDataPath: ''
  })

  assert.equal(merged.length, 1)
  assert.equal(merged[0].table_name, 'ball_by_ball_ipl')
  assert.equal(merged[0].file_path, 'browser://ball_by_ball_ipl')
})

test('mergeDatasetSources includes active browser table from current path', () => {
  const merged = mergeDatasetSources({
    catalogDatasets: [],
    runtimeTables: [],
    currentDataPath: '/browser:/ball_by_ball_ipl'
  })

  assert.equal(merged.length, 1)
  assert.equal(merged[0].table_name, 'ball_by_ball_ipl')
  assert.equal(merged[0].file_path, 'browser://ball_by_ball_ipl')
})
