import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function readSource(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

function extractBlock(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(start, -1, `Missing marker: ${startMarker}`)
  assert.notEqual(end, -1, `Missing marker: ${endMarker}`)
  return source.slice(start, end)
}

test('workspace tab shows inline dataset processing card and consumes websocket progress', () => {
  const source = readSource('src/components/modals/tabs/WorkspaceTab.vue')
  const ingestBlock = extractBlock(
    source,
    'async function startBatchDatasetIngestion(paths) {',
    'async function retryLastDatasetIngestion() {',
  )

  assert.equal(source.includes('v-if="isDatasetIngesting"'), true)
  assert.equal(source.includes('{{ datasetIngestStatusLabel }}'), true)
  assert.equal(source.includes('settingsWebSocket.subscribeProgress(handleSettingsProgressUpdate)'), true)
  assert.equal(source.includes('function handleSettingsProgressUpdate(data) {'), true)
  assert.equal(source.includes('async function ensureWorkspaceIdentityPersisted({'), true)
  assert.equal(source.includes('startDatasetIngest(sourcePaths.length === 1 ? sourcePaths[0] : `${sourcePaths.length} selected files`)'), true)
  assert.equal(source.includes('const identityReady = await ensureWorkspaceNamePersisted({ silent: true })'), true)
  assert.equal(source.includes('if (!identityReady) return'), true)
  assert.equal(source.includes('trackDatasetIngestionJob(workspaceId, jobId)'), true)
  assert.equal(source.includes("setWorkspaceOperation('ingest', 'Importing selected datasets into the workspace.')"), true)
  assert.equal(source.includes('toast.success(\'Datasets added\''), false)
  assert.equal(source.includes("toast.success('Schema ready'"), true)
  assert.equal(source.includes("window.dispatchEvent(new CustomEvent('dataset-schema-ready'"), true)
  assert.equal(source.includes('trackSchemaReadyNotificationsFromIngestionJob(job)'), true)
  assert.equal(source.includes('notifyReadyDatasetSchemas(datasetEntries.value)'), true)
  assert.equal(source.includes('setupStep'), false)
  assert.equal(ingestBlock.includes('await appStore.ensureWorkspaceKernelConnected(workspaceId)'), false)
  assert.equal(source.includes('void generateWorkspaceSchemas({'), false)
  assert.equal(source.includes('autoStart: true'), false)
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

test('workspace delete uses a shared confirmation modal from the workspace list', () => {
  const source = readSource('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(source.includes('isWorkspaceDeleteDialogOpen'), true)
  assert.equal(source.includes('workspaceDeleteDialogMessage'), true)
  assert.equal(source.includes('@click.stop="requestDeleteWorkspace(workspace.id)"'), true)
  assert.equal(source.includes('title="Delete workspace"'), true)
  assert.equal(source.includes('aria-label="Delete workspace"'), true)
  assert.equal(source.includes('group-hover:opacity-100'), true)
  assert.equal(source.includes('showDeleteConfirm'), false)
  assert.equal(source.includes('Danger zone'), false)
})

test('workspace tab disables dataset mutation until the inspected workspace is activated', () => {
  const source = readSource('src/components/modals/tabs/WorkspaceTab.vue')

  assert.equal(source.includes('const requiresWorkspaceActivation = computed(() => !isWorkspaceActive.value)'), true)
  assert.equal(source.includes('v-if="isWorkspaceActive"'), true)
  assert.equal(source.includes('Activate this workspace to add datasets.'), true)
  assert.equal(source.includes("toast.info('Activate workspace first', 'Activate this workspace before importing datasets.')"), true)
  assert.equal(source.includes("toast.info('Activate workspace first', 'Activate this workspace before generating schemas.')"), true)
})
