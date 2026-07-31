import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const editor = readFileSync(new URL('../src/components/preview/SchemaEditorTab.vue', import.meta.url), 'utf8')
const preview = readFileSync(new URL('../src/components/schema/TableDataPreview.vue', import.meta.url), 'utf8')

test('workspace data exposes lazy Schema and Preview modes for a selected table', () => {
  assert.match(editor, /tableViewOptions/)
  assert.match(editor, /value: 'schema'/)
  assert.match(editor, /value: 'preview'/)
  assert.match(editor, /<TableDataPreview\s+v-else/)
  assert.match(editor, /<WorkspaceDataSources\s+v-show=/)
  assert.doesNotMatch(editor, /<WorkspaceDataSources\s+v-else/)
})

test('saved dataset previews reuse the shared dataframe table and support both edges', () => {
  assert.match(preview, /import DataTable from '..\/analysis\/table\/DataTable\.vue'/)
  assert.match(preview, /label: 'First 100'/)
  assert.match(preview, /label: 'Last 100'/)
  assert.match(preview, /session-cached snapshot/)
})
