import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('preview service accepts table override for schema and preview fetches', () => {
  const servicePath = resolve(process.cwd(), 'src/services/previewService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('getDataPreview(sampleType = \'random\', forceRefresh = false, tableNameOverride = null)'), true)
  assert.equal(source.includes('loadSchema(filepath, forceRefresh = false, tableNameOverride = null)'), true)
  assert.equal(source.includes('tableNameOverride ||'), true)
})

test('api service exposes v1 regenerate schema endpoint for workspace datasets', () => {
  const servicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(servicePath, 'utf-8')

  assert.equal(source.includes('async v1RegenerateDatasetSchema(workspaceId, tableName, payload = {})'), true)
  assert.equal(source.includes('/api/v1/workspaces/${workspaceId}/datasets/${encodeURIComponent(tableName)}/schema/regenerate'), true)
})

test('schema editor auto-regenerates on dataset switch/load failures with progress modal flow', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('await regenerateSchemaForPath(dataPath, appStore.ingestedTableName || null)'), true)
  assert.equal(source.includes('loadError?.status === 422 || loadError?.response?.status === 422'), true)
  assert.equal(source.includes('const newTableName = event?.detail?.tableName'), true)
  assert.equal(source.includes('apiService.v1RegenerateDatasetSchema('), true)
})

test('schema editor does not label blank descriptions as active generation', () => {
  const schemaEditorPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaEditorPath, 'utf-8')

  assert.equal(source.includes('Schema Descriptions Not Generated Yet'), true)
  assert.equal(source.includes('Schema Generation in Progress'), false)
  assert.equal(source.includes('const schemaNeedsDescriptions = computed(() => {'), true)
})

test('preview tab forwards selected table name on dataset switch refresh', () => {
  const previewTabPath = resolve(process.cwd(), 'src/components/preview/PreviewTab.vue')
  const source = readFileSync(previewTabPath, 'utf-8')

  assert.equal(source.includes('const tableNameOverride = event?.detail?.tableName || appStore.ingestedTableName || null'), true)
  assert.equal(source.includes('fetchDataPreview(true, tableNameOverride)'), true)
  assert.equal(source.includes('fetchSchemaData(true, tableNameOverride)'), true)
})
