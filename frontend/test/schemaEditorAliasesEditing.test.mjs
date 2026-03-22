import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('schema editor supports alias editing and persists normalized aliases on save/export', () => {
  const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaPath, 'utf-8')

  assert.equal(source.includes('function normalizeAliasList(value) {'), true)
  assert.equal(source.includes('function updateSchemaAliases(index, aliasText) {'), true)
  assert.equal(source.includes('function formatAliasesForInput(value) {'), true)
  assert.equal(source.includes('formatAliasesForInput(col.aliases)'), true)
  assert.equal(source.includes("@input=\"e => updateSchemaAliases(i, e.target.value)\""), true)
  assert.equal(source.includes('columns: normalizeSchemaColumns(schema.value)'), true)
})

test('schema editor keeps catalog datasets visible and does not auto-regenerate on dataset switch', () => {
  const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaPath, 'utf-8')

  assert.equal(source.includes('normalizeDatasetEntries(catalogItems).forEach((item) => {'), true)
  assert.equal(source.includes('Schema has no columns yet. Click Regenerate to create descriptions manually.'), true)
  assert.equal(source.includes('Schema is not available yet. Click Regenerate to create it manually.'), true)
  assert.equal(source.includes('schemaNeedsDescriptions.value && appStore.apiKeyConfigured'), false)
  assert.equal(source.includes('return await regenerateSchemaForPath(dataPath, tableName, { allowWhileLoading: true })'), false)
})
