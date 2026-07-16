import test from 'node:test'
import assert from 'node:assert/strict'
import { datasetImportLabel } from '../src/utils/datasetImport.js'
import { filenameFromPath } from '../src/utils/pathUtils.js'

test('filenameFromPath handles posix and Windows paths', () => {
  assert.equal(filenameFromPath('/tmp/report.csv'), 'report.csv')
  assert.equal(filenameFromPath('C:\\Users\\me\\Downloads\\report.csv'), 'report.csv')
  assert.equal(filenameFromPath('', 'dataset'), 'dataset')
})

test('datasetImportLabel handles Windows paths', () => {
  assert.equal(
    datasetImportLabel(['C:\\Users\\me\\Downloads\\sales.xlsx']),
    'sales.xlsx'
  )
})
