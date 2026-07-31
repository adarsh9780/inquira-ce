import test from 'node:test'
import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { readFileSync } from './sourceText.mjs'

const editor = readFileSync(resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue'), 'utf-8')

test('schema hub uses focused table navigation and protects unsaved metadata', () => {
  assert.equal(editor.includes('<SchemaTableNavigator'), true)
  assert.equal(editor.includes('@select="requestSchemaSelection"'), true)
  assert.equal(editor.includes("title=\"Discard unsaved changes?\""), true)
  assert.equal(editor.includes('schemaHub.resetTable(currentTable.id)'), true)
  assert.equal(editor.includes(':disabled="schemaBusy || schemaHub.isEdited.value"'), true)
  assert.equal(editor.includes('data-action="add-workspace-data"'), true)
  assert.equal(editor.includes('@click="requestAddData"'), true)
  assert.equal(editor.includes('<WorkspaceDataSources'), true)
  assert.equal(editor.includes('handleRequestedAddData'), true)
  assert.equal(editor.includes('handledWorkspaceDataRequestIds.set(workspaceStore, requestId)'), true)
})
