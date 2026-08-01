import assert from 'node:assert/strict'
import test from 'node:test'
import { resolve } from 'node:path'

import { readFileSync } from './sourceText.mjs'

const editor = readFileSync(resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue'), 'utf8')
const context = readFileSync(resolve(process.cwd(), 'src/components/schema/TableContextSurface.vue'), 'utf8')
const metadata = readFileSync(resolve(process.cwd(), 'src/components/schema/TableMetadataSurface.vue'), 'utf8')

test('selected dataset identity has one persistent detail heading', () => {
  assert.match(editor, /<h3[^>]*>\{\{ schemaHub\.selectedTable\.value\.tableName \}\}<\/h3>/)
  assert.doesNotMatch(metadata, /<h3[^>]*table\.tableName/)
  assert.doesNotMatch(metadata, /table\.rowCount\.toLocaleString/)
  assert.doesNotMatch(editor, /:header="schemaHub\.selectedTable\.value\?\.tableName/)
})

test('context and schema chrome stay compact around the shared data grid', () => {
  assert.match(context, /<h3[^>]*>Context<\/h3>/)
  assert.doesNotMatch(context, /bg-\[var\(--color-base-soft\)\]/)
  assert.match(metadata, /:fill="true"/)
  assert.doesNotMatch(metadata, /rounded-xl/)
  assert.doesNotMatch(metadata, /<section[^>]*shadow-sm/)
  assert.match(editor, /v-if="tableView === 'schema'" class="min-h-0 flex-1 overflow-hidden"/)
})
