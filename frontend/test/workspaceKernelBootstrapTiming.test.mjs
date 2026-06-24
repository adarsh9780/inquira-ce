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
  const appSource = readFileSync(resolve(process.cwd(), 'src/App.vue'), 'utf-8')

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
  const selectConversationBlock = extractBlock(
    source,
    'function setActiveConversationId(conversationId) {',
    'function setTurnViewEnabled(enabled) {',
  )
  const fetchConversationsBlock = extractBlock(
    source,
    'async function fetchConversations() {',
    'async function createConversation(title = null) {',
  )
  const fetchTurnsBlock = extractBlock(
    source,
    'async function fetchConversationTurns({ reset = true, preferLatest = false } = {}) {',
    'async function deleteConversationById(conversationId) {',
  )

  assert.equal(fetchBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(createBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(activateBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(selectConversationBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(fetchConversationsBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(fetchTurnsBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(appSource.includes("appBootstrap.message = 'Starting your workspace runtime...'"), false)
  assert.equal(appSource.includes('await appStore.ensureWorkspaceRuntimeReady(appStore.activeWorkspaceId)'), false)
})

test('workspace creation and mounted panes do not warm runtimes implicitly', () => {
  const tabPath = resolve(process.cwd(), 'src/components/modals/tabs/WorkspaceTab.vue')
  const source = readFileSync(tabPath, 'utf-8')
  const chatInput = readFileSync(resolve(process.cwd(), 'src/components/chat/ChatInput.vue'), 'utf-8')
  const codeTab = readFileSync(resolve(process.cwd(), 'src/components/analysis/CodeTab.vue'), 'utf-8')
  const uploadBlock = extractBlock(
    source,
    'async function startBatchDatasetIngestion(paths) {',
    'async function retryLastDatasetIngestion() {',
  )
  assert.equal(uploadBlock.includes('await appStore.ensureWorkspaceRuntimeReady(workspaceId)'), false)
  assert.equal(uploadBlock.includes('await appStore.startDatasetIngestion(sourcePaths'), true)
  assert.equal(source.includes('async function warmWorkspaceRuntimeInBackground(workspaceId)'), false)
  assert.equal(source.includes('void warmWorkspaceRuntimeInBackground(workspaceId)'), false)
  assert.equal(chatInput.includes('void appStore.fetchColumnCatalog({ force: true })'), false)
  assert.equal(codeTab.includes('await appStore.fetchColumnCatalog({ force: true })'), false)
})

test('column catalog path uses saved schema metadata without runtime bootstrap', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = readFileSync(appStorePath, 'utf-8')
  const catalogBlock = extractBlock(
    source,
    'async function fetchColumnCatalog({ force = false } = {}) {',
    'async function ensureWorkspaceRuntimeReady(workspaceId = activeWorkspaceId.value) {',
  )
  assert.equal(catalogBlock.includes('ensureWorkspaceRuntimeReady('), false)
  assert.equal(catalogBlock.includes('apiService.getWorkspaceColumns(workspaceId)'), false)
  assert.equal(catalogBlock.includes('apiService.v1ListDatasets(workspaceId)'), true)
  assert.equal(catalogBlock.includes('apiService.v1GetDatasetSchema(workspaceId, tableName)'), true)
})

test('missing saved dataframe artifacts clear stale table selection without startup error', () => {
  const tableTabPath = resolve(process.cwd(), 'src/components/analysis/TableTab.vue')
  const source = readFileSync(tableTabPath, 'utf-8')

  assert.equal(source.includes('function isArtifactMissingError(error) {'), true)
  assert.equal(source.includes('function clearMissingSelectedArtifact(artifactId) {'), true)
  assert.equal(source.includes("appStore.setSelectedTableArtifact(workspaceId, '')"), true)
  assert.equal(source.includes('clearMissingSelectedArtifact(artifactId)'), true)
  assert.equal(source.includes('clearMissingSelectedArtifact(aid)'), true)
  assert.equal(source.includes('params.successCallback([], 0)'), true)
})
