import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('api service does not expose legacy dataset routes or helper shims', () => {
  const source = readFileSync(
    resolve(process.cwd(), 'src/services/apiService.js'),
    'utf-8',
  )

  assert.equal(source.includes('async listDatasets() {'), false)
  assert.equal(source.includes('async setDataPathSimple(dataPath) {'), false)
  assert.equal(source.includes('async checkDatasetHealth(tableName) {'), false)
  assert.equal(source.includes('async deleteDataset(tableName) {'), false)
  assert.equal(source.includes('async refreshDataset(tableName, regenerateSchema = true) {'), false)
  assert.equal(source.includes('async downloadDatasetBlob(tableName) {'), false)
  assert.equal(source.includes('async setDataPath(dataPath) {'), false)
  assert.equal(source.includes('/datasets/${tableName}'), false)
})
