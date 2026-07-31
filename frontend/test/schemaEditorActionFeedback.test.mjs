import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

test('schema editor actions emit feedback and keep refresh, save, and regeneration flows wired', () => {
  const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaPath, 'utf-8')

  assert.equal(source.includes("import { toast } from '../../composables/useToast'"), true)
  assert.equal(source.includes("toast.success('Table schema saved'"), true)
  assert.equal(source.includes("toast.success('Schema refreshed'"), true)
  assert.equal(source.includes("toast.success('Table schema regenerated'"), true)
  assert.equal(source.includes('async function fetchWorkspaceSchema(forceRefresh = false)'), true)
  assert.equal(source.includes('async function saveTableSchema(tableId'), true)
  assert.equal(source.includes('async function regenerateTableSchema(tableName)'), true)
  assert.equal(source.includes('await workspaceApi.saveDatasetSchema(workspaceId, table.tableName, {'), true)
  assert.equal(source.includes('await workspaceApi.regenerateDatasetSchema(workspaceStore.activeWorkspaceId, tableName, {'), true)
})
