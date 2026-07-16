import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('v1 dataset API contract includes remove and deletion-job endpoints with apiService wrappers', () => {
  const contractSource = readFileSync(resolve(process.cwd(), 'src/services/contracts/v1Api.js'), 'utf-8')
  const serviceSource = readFileSync(resolve(process.cwd(), 'src/services/apiService.js'), 'utf-8')

  assert.equal(contractSource.includes('remove: (workspaceId, tableName) =>'), true)
  assert.equal(contractSource.includes('/datasets/${encodeURIComponent(tableName)}'), true)
  assert.equal(contractSource.includes('deletions: (workspaceId) =>'), true)
  assert.equal(contractSource.includes('deletionById: (workspaceId, jobId) =>'), true)
  assert.equal(serviceSource.includes('async v1DeleteDataset(workspaceId, tableName) {'), true)
  assert.equal(serviceSource.includes('return v1Api.datasets.remove(workspaceId, tableName)'), true)
  assert.equal(serviceSource.includes('async v1ListDatasetDeletionJobs(workspaceId) {'), true)
  assert.equal(serviceSource.includes('return v1Api.datasets.deletions(workspaceId)'), true)
  assert.equal(serviceSource.includes('async v1GetDatasetDeletionJob(workspaceId, jobId) {'), true)
  assert.equal(serviceSource.includes('return v1Api.datasets.deletionById(workspaceId, jobId)'), true)
})
