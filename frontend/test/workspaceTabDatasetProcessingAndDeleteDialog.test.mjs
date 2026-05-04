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
  assert.equal(source.includes('async function goToSetupStep(stepId) {'), true)
  assert.equal(source.includes('const persisted = await ensureWorkspaceIdentityPersisted({ silent: true })'), true)
  assert.equal(source.includes('async function ensureWorkspaceIdentityPersisted({ silent = false } = {}) {'), true)
  assert.equal(source.includes('startDatasetIngest(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths.length} selected files`)'), true)
  assert.equal(source.includes('const identityReady = await ensureWorkspaceIdentityPersisted({ silent: true })'), true)
  assert.equal(source.includes('if (!identityReady) return'), true)
  assert.equal(source.includes('trackDatasetIngestionJob(workspaceId, jobId)'), true)
  assert.equal(source.includes("setWorkspaceOperation('ingest', 'Importing selected datasets into the workspace.')"), true)
  assert.equal(source.includes('if (completedCount > 0) {'), true)
  assert.equal(source.includes('setupStep.value = 3'), true)
  assert.equal(source.includes('clearWorkspaceOperation()'), true)
  assert.equal(source.includes('const datasetIngestError = ref(\'\')'), true)
  assert.equal(source.includes('const datasetIngestHasError = computed(() => Boolean(String(datasetIngestError.value || \'\').trim()))'), true)
  assert.equal(source.includes('v-if="datasetIngestHasError"'), true)
  assert.equal(source.includes('@click="retryLastDatasetIngestion"'), true)
  assert.equal(source.includes('function markDatasetIngestFailed(message) {'), true)
  assert.equal(source.includes('lastSelectedDatasetPaths.value = [...sourcePaths]'), true)
  assert.equal(source.includes('await new Promise((resolve) => setTimeout(resolve, 700))'), true)
  assert.equal(source.includes('datasetIngestPercent.value = 100'), true)
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

test('workspace delete uses shared confirmation modal from list and detail', () => {
  const source = readSource('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(source.includes('isWorkspaceDeleteDialogOpen'), true)
  assert.equal(source.includes('workspaceDeleteDialogMessage'), true)
  assert.equal(source.includes('@click.stop="requestDeleteWorkspace(workspace.id)"'), true)
  assert.equal(source.includes('@click="requestDeleteWorkspace(activeWorkspaceId)"'), true)
  assert.equal(source.includes('title="Delete workspace"'), true)
  assert.equal(source.includes('aria-label="Delete workspace"'), true)
  assert.equal(source.includes('group-hover:opacity-100'), false)
  assert.equal(source.includes('showDeleteConfirm'), false)
  assert.equal(source.includes('Danger zone'), false)
})
