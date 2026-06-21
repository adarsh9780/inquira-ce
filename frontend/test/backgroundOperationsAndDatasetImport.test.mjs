import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

function read(relativePath) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf-8')
}

test('app store exposes foreground and background operation state with status helpers', () => {
  const store = read('src/stores/appStore.js')

  assert.equal(store.includes('const foregroundOperation = ref(null)'), true)
  assert.equal(store.includes('const backgroundOperations = ref([])'), true)
  assert.equal(store.includes('const primaryBackgroundOperation = computed(() => {'), true)
  assert.equal(store.includes('function startForegroundOperation(payload = {})'), true)
  assert.equal(store.includes('function startBackgroundOperation(payload = {})'), true)
  assert.equal(store.includes('function finishBackgroundOperation(operationId, payload = {})'), true)
})

test('status bar renders active background operation progress without replacing workspace status', () => {
  const statusBar = read('src/components/layout/StatusBar.vue')

  assert.equal(statusBar.includes('data-background-operation-status'), true)
  assert.equal(statusBar.includes('primaryBackgroundOperationLabel'), true)
  assert.equal(statusBar.includes('backgroundOperationCountLabel'), true)
  assert.equal(statusBar.includes('inquira-spinner'), true)
  assert.equal(statusBar.includes('data-workspace-switcher'), true)
  assert.equal(statusBar.includes('workspaceRuntimeStatusMeta'), true)
})

test('global dataset import supports Cmd/Ctrl+O and app-level drops through shared ingestion', () => {
  const app = read('src/App.vue')

  assert.equal(app.includes("matchShortcut(event, 'dataset-import')"), true)
  assert.equal(app.includes('void openGlobalDatasetPicker()'), true)
  assert.equal(app.includes("import('@tauri-apps/plugin-dialog')"), true)
  assert.equal(app.includes('document.addEventListener(\'dragover\', handleAppDatasetDragOver)'), true)
  assert.equal(app.includes('document.addEventListener(\'drop\', handleAppDatasetDrop)'), true)
  assert.equal(app.includes('await appStore.startDatasetIngestion(sourcePaths'), true)
  assert.equal(app.includes('getCurrentWebview().onDragDropEvent'), true)
  assert.equal(app.includes("toast.error('Desktop Only', 'Local dataset drops are only available in the desktop app.')"), true)
})
