import test from 'node:test'
import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { readFileSync } from './sourceText.mjs'

const editor = readFileSync(resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue'), 'utf-8')

test('workspace manager keeps table navigation focused and protects unsaved metadata', () => {
  assert.equal(editor.includes('<SchemaTableNavigator'), true)
  assert.equal(editor.includes('@select="requestSchemaSelection"'), true)
  assert.equal(editor.includes('title="Discard unsaved changes?"'), true)
  assert.equal(editor.includes('schemaHub.resetTable(currentTable.id)'), true)
  assert.equal(editor.includes(':disabled="!hasWorkspace || schemaBusy || schemaHub.isEdited.value"'), true)
})

test('workspace manager owns direct source and dataset actions', () => {
  assert.equal(editor.includes('data-action="add-workspace-data"'), true)
  assert.equal(editor.includes('@click="requestAddData"'), true)
  assert.equal(editor.includes('<WorkspaceDataSources'), true)
  assert.equal(editor.includes('handleRequestedAddData'), true)
  assert.equal(editor.includes('handledWorkspaceDataRequestIds.set(workspaceStore, requestId)'), true)
  assert.equal(editor.includes("id: 'remove-dataset'"), true)
  assert.equal(editor.includes('title="Remove dataset?"'), true)
  assert.equal(editor.includes('workspaceApi.removeDataset(workspaceId, table.tableName)'), true)
  assert.equal(editor.includes('dataSourcesRef.value?.reload()'), true)
})

test('source drawer and dataset menu close through shared dismissal behavior', () => {
  assert.equal(editor.includes('data-source-drawer-backdrop'), true)
  assert.equal(editor.includes('@pointerdown.self="closeSourceDrawer"'), true)
  assert.equal(editor.includes("event.key === 'Escape' && sourceDrawerOpen.value"), true)
  assert.equal(editor.includes('<FloatingActionMenu'), true)
  assert.equal(editor.includes('@close="datasetMenuOpen = false"'), true)
})
