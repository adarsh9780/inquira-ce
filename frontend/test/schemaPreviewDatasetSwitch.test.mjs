import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('preview service accepts table override for schema loads', () => {
  const servicePath = resolve(process.cwd(), 'src/services/previewService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('loadSchema(filepath, forceRefresh = false, tableNameOverride = null)'), true)
  assert.equal(source.includes('tableNameOverride ||'), true)
  assert.equal(source.includes('clearSchemaCache()'), true)
})

test('api service exposes v1 regenerate schema endpoint for workspace datasets', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('async v1RegenerateDatasetSchema(workspaceId, tableName, payload = {})'), true)
  assert.equal(source.includes('/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema/regenerate'), true)
})

test('schema editor waits for manual regeneration when a dataset switch finds no schema yet', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('Schema has no columns yet. Click Regenerate to create descriptions manually.'), true)
  assert.equal(source.includes('Schema is not available yet. Click Regenerate to create it manually.'), true)
  assert.equal(source.includes('return await regenerateSchemaForPath('), false)
  assert.equal(source.includes('allowWhileLoading: true'), false)
  assert.equal(source.includes('loadError?.status === 422 || loadError?.response?.status === 422'), true)
  assert.equal(source.includes('const newTableName = event?.detail?.tableName'), true)
  assert.equal(source.includes('apiService.v1RegenerateDatasetSchema('), true)
})

test('schema editor derives dataset options from workspace tables and does not require source_path for selection', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('function extractWorkspaceTableNames(columns)'), true)
  assert.equal(source.includes('function buildSchemaDatasetEntries(catalogItems, workspaceColumns)'), true)
  assert.equal(source.includes('apiService.getWorkspaceColumns(workspaceId)'), true)
  assert.equal(source.includes('apiService.v1GetWorkspaceColumns(workspaceId)'), false)
  assert.equal(source.includes('if (!normalizedPath && !(saveTableName && appStore.activeWorkspaceId)) {'), true)
  assert.equal(source.includes('if (!selected?.sourcePath) return'), false)
})

test('schema editor does not label blank descriptions as active generation', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('Schema Descriptions Not Generated Yet'), true)
  assert.equal(source.includes('Schema Generation in Progress'), false)
  assert.equal(source.includes('const schemaNeedsDescriptions = computed(() => {'), true)
})

test('code tab default template includes deterministic duckdb samples', () => {
  const codeTabPath = resolve(process.cwd(), 'src/components/analysis/CodeTab.vue')
  const source = readFileSync(codeTabPath, 'utf-8')

  assert.equal(source.includes('head_100 = conn.sql('), true)
  assert.equal(source.includes('tail_100 = conn.sql('), true)
  assert.equal(source.includes('sample_100 = conn.sql('), true)
  assert.equal(source.includes("SELECT 'head' AS sample_bucket"), true)
  assert.equal(source.includes("SELECT 'tail' AS sample_bucket"), true)
  assert.equal(source.includes("SELECT 'sample' AS sample_bucket"), true)
})
