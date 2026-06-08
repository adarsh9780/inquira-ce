import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
const source = readFileSync(schemaPath, 'utf-8')

test('schema editor supports inline alias editing and persists normalized aliases', () => {
  assert.equal(source.includes('function normalizeAliasList(value) {'), true)
  assert.equal(source.includes("startInlineEdit(col, 'aliases')"), true)
  assert.equal(source.includes("editingCell?.field === 'aliases'"), true)
  assert.equal(source.includes('const newAliases = normalizeAliasList(value)'), true)
  assert.equal(source.includes('aliases: c.aliases || []'), true)
})

test('schema editor loads all workspace dataset schemas without auto-regenerating them', () => {
  assert.equal(source.includes('const datasetResponse = await apiService.v1ListDatasets(workspaceId)'), true)
  assert.equal(source.includes('return await apiService.v1GetDatasetSchema(workspaceId, ds.table_name)'), true)
  assert.equal(source.includes('await fetchWorkspaceSchema()'), true)
  assert.equal(source.includes('regenerateTableSchema(group.tableName)'), true)
})
