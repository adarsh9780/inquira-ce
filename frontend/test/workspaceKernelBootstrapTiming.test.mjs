import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function extractBlock(source, startMarker, endMarker) {
  const start = source.indexOf(startMarker)
  const end = source.indexOf(endMarker, start + startMarker.length)
  assert.notEqual(start, -1, `Missing marker: ${startMarker}`)
  assert.notEqual(end, -1, `Missing marker: ${endMarker}`)
  return source.slice(start, end)
}

test('workspace listing no longer bootstraps runtimes as a side effect', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(appStorePath, 'utf-8')

  const fetchBlock = extractBlock(
    source,
    'async function fetchWorkspaces() {',
    'async function createWorkspace(name, schemaContext = \'\') {',
  )
  const createBlock = extractBlock(
    source,
    'async function createWorkspace(name, schemaContext = \'\') {',
    'async function activateWorkspace(workspaceId) {',
  )
  const activateBlock = extractBlock(
    source,
    'async function activateWorkspace(workspaceId) {',
    'async function fetchConversations() {',
  )

  assert.equal(fetchBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(createBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(activateBlock.includes('ensureWorkspaceRuntimeReady('), false)
})

test('workspace creation starts hidden runtime warmup and batch dataset import does not block on frontend runtime readiness', () => {
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')
  const source = readFileSync(tabPath, 'utf-8')
  const uploadBlock = extractBlock(
    source,
    'async function startBatchDatasetIngestion(paths) {',
    'async function retryLastDatasetIngestion() {',
  )
  const warmupBlock = extractBlock(
    source,
    'async function warmWorkspaceRuntimeInBackground(workspaceId) {',
    'function datasetSchemaStatusState(dataset) {',
  )
  assert.equal(uploadBlock.includes('await appStore.ensureWorkspaceRuntimeReady(workspaceId)'), false)
  assert.equal(uploadBlock.includes('await appStore.startDatasetIngestion(sourcePaths'), true)
  assert.equal(warmupBlock.includes('await appStore.ensureWorkspaceRuntimeReady(targetWorkspaceId)'), true)
})

test('column catalog path bootstraps runtime before loading columns', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(appStorePath, 'utf-8')
  const catalogBlock = extractBlock(
    source,
    'async function fetchColumnCatalog({ force = false } = {}) {',
    'async function ensureWorkspaceRuntimeReady(workspaceId = activeWorkspaceId.value) {',
  )
  assert.equal(catalogBlock.includes('await ensureWorkspaceRuntimeReady(workspaceId)'), true)
  assert.equal(catalogBlock.includes('apiService.getWorkspaceColumns(workspaceId)'), true)
})
