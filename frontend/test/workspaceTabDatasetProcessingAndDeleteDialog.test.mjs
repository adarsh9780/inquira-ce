import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('workspace tab shows inline dataset processing card and consumes websocket progress', () => {
  const source = readSource('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(source.includes('v-if="isDatasetIngesting"'), true)
  assert.equal(source.includes('{{ datasetIngestStatusLabel }}'), true)
  assert.equal(source.includes('datasetIngestPercent !== null'), true)
  assert.equal(source.includes('settingsWebSocket.subscribeProgress(handleSettingsProgressUpdate)'), true)
  assert.equal(source.includes('function handleSettingsProgressUpdate(data) {'), true)
  assert.equal(source.includes('startDatasetIngest(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths.length} selected files`)'), true)
  assert.equal(source.includes('trackDatasetIngestionJob(workspaceId, jobId)'), true)
})

test('workspace tab uses modal confirmation for dataset deletion and polls cleanup job', () => {
  const source = readSource('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(source.includes('<ConfirmationModal'), true)
  assert.equal(source.includes('pendingRemovalTable === dataset.table_name'), false)
  assert.equal(source.includes('isDatasetDeleteDialogOpen'), true)
  assert.equal(source.includes('const job = await apiService.v1DeleteDataset(workspaceId, tableName)'), true)
  assert.equal(source.includes('trackDatasetDeletionJob(workspaceId, jobId, datasetLabel)'), true)
  assert.equal(source.includes('apiService.v1GetDatasetDeletionJob('), true)
  assert.equal(source.includes('apiService.v1ListDatasetDeletionJobs(workspaceId)'), true)
})
