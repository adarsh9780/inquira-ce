import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const source = readFileSync(resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue'), 'utf-8')

test('workspace setup combines context and dataset management without steps', () => {
  assert.equal(source.includes('Workspace Context'), true)
  assert.equal(source.includes('Linked Datasets'), true)
  assert.equal(source.includes('@click="saveWorkspaceContext"'), true)
  assert.equal(source.includes('setupSteps'), false)
  assert.equal(source.includes('setupStep'), false)
  assert.equal(source.includes('workspace-stepper'), false)
})

test('workspace dataset view keeps one import target and schema management actions', () => {
  assert.equal(source.includes('data-testid="workspace-import-datasets-dropzone"'), true)
  assert.equal(source.includes('data-testid="workspace-import-datasets-header"'), false)
  assert.equal(source.includes('data-testid="workspace-import-datasets-empty"'), false)
  assert.equal(source.includes('title="Regenerate schema"'), true)
  assert.equal(source.includes('title="Remove dataset"'), true)
  assert.equal(source.includes('apiService.v1EnqueueDatasetSchemaRegeneration('), true)
})

test('workspace dataset flow relies on persisted schema status', () => {
  assert.equal(source.includes('function datasetSchemaStatusLabel(dataset) {'), true)
  assert.equal(source.includes('function datasetSchemaStatusBadgeClass(dataset) {'), true)
  assert.equal(source.includes('function syncDatasetSchemaPolling() {'), true)
  assert.equal(source.includes('async function generateWorkspaceSchemas('), false)
})
