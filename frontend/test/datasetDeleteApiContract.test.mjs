import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('v1 dataset API contract includes remove and deletion-job endpoints with apiService wrappers', () => {
  const contractSource = readFileSync(resolve(process.cwd(), 'src/services/apiClient.ts'), 'utf-8')
  const generatedSource = readFileSync(resolve(process.cwd(), 'src/services/generatedApi.ts'), 'utf-8')
  const serviceSource = readFileSync(resolve(process.cwd(), 'src/services/apiRuntime.js'), 'utf-8')

  assert.equal(contractSource.includes('remove: (workspaceId: string, tableName: string)'), true)
  assert.equal(generatedSource.includes('/datasets/${tableName}'), true)
  assert.equal(contractSource.includes('deletions: (workspaceId: string)'), true)
  assert.equal(contractSource.includes('deletionById: (workspaceId: string, jobId: string)'), true)
  assert.equal(serviceSource.includes('async v1DeleteDataset(workspaceId, tableName) {'), true)
  assert.equal(serviceSource.includes('return v1Api.datasets.remove(workspaceId, tableName)'), true)
  assert.equal(serviceSource.includes('async v1ListDatasetDeletionJobs(workspaceId) {'), true)
  assert.equal(serviceSource.includes('return v1Api.datasets.deletions(workspaceId)'), true)
  assert.equal(serviceSource.includes('async v1GetDatasetDeletionJob(workspaceId, jobId) {'), true)
  assert.equal(serviceSource.includes('return v1Api.datasets.deletionById(workspaceId, jobId)'), true)
})
