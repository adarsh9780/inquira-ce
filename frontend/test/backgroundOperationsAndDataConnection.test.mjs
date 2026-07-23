import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('app store exposes background operation state with the helpers used by the UI', () => {
  const store = `${read('src/stores/appStore.js')}\n${read('src/stores/executionStore.ts')}`

  assert.match(store, /const backgroundOperations = ref(?:<[^>]+>)?\(\[\]\)/)
  assert.equal(store.includes('const activeBackgroundOperations = computed(() => {'), true)
  assert.equal(store.includes('const primaryBackgroundOperation = computed(() => {'), true)
  assert.equal(store.includes('function startBackgroundOperation(payload = {})'), true)
  assert.equal(store.includes('function finishBackgroundOperation(operationId, payload = {})'), true)
  assert.equal(store.includes('startBackgroundOperation,'), true)
  assert.equal(store.includes('finishBackgroundOperation,'), true)
})

test('status bar renders active background operations while the context bar owns workspace identity', () => {
  const statusBar = read('src/components/layout/StatusBar.vue')
  const contextBar = read('src/components/layout/WorkspaceContextBar.vue')

  assert.equal(statusBar.includes('data-background-operation-status'), true)
  assert.equal(statusBar.includes('primaryBackgroundOperationLabel'), true)
  assert.equal(statusBar.includes('backgroundOperationCountLabel'), true)
  assert.equal(statusBar.includes('inquira-spinner'), true)
  assert.equal(statusBar.includes('data-workspace-switcher'), false)
  assert.equal(statusBar.includes('workspaceRuntimeStatusMeta'), true)
  assert.equal(contextBar.includes('data-workspace-context-bar'), true)
  assert.equal(contextBar.includes('data-workspace-status'), true)
})

test('global data actions open the connection flow from shortcuts and file drops', () => {
  const app = read('src/App.vue')

  assert.equal(app.includes("matchShortcut(event, 'dataset-import')"), true)
  assert.equal(app.includes('void openGlobalDatasetPicker()'), true)
  assert.equal(app.includes('document.addEventListener(\'dragover\', handleAppDatasetDragOver)'), true)
  assert.equal(app.includes('document.addEventListener(\'drop\', handleAppDatasetDrop)'), true)
  assert.equal(app.includes('appStore.openDataConnectionFlow()'), true)
  assert.equal(app.includes('startDatasetIngestion'), false)
})
