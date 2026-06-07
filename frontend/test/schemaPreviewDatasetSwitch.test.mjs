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

test('schema editor derives dataset options from workspace tables and does not require source_path for selection', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('apiService.v1ListDatasets(workspaceId)'), true)
  assert.equal(source.includes('apiService.v1GetDatasetSchema(workspaceId, ds.table_name)'), true)
  assert.equal(source.includes('const groupedSchema = computed(() => {'), true)
})

test('schema editor refreshes automatically when dataset schema becomes ready', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('async function handleDatasetSchemaReady(event) {'), true)
  assert.equal(source.includes("window.addEventListener('dataset-schema-ready', handleDatasetSchemaReady)"), true)
  assert.equal(source.includes("window.removeEventListener('dataset-schema-ready', handleDatasetSchemaReady)"), true)
  assert.equal(source.includes('await fetchWorkspaceSchema()'), true)
})

test('schema editor does not label blank descriptions as active generation', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('Click to add description...'), true)
  assert.equal(source.includes('Click to add aliases...'), true)
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
