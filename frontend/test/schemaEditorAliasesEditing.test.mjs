import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from './sourceText.mjs'
import { resolve } from 'node:path'

const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
const source = readFileSync(schemaPath, 'utf-8')
const statePath = resolve(process.cwd(), 'src/composables/useSchemaHubState.ts')
const stateSource = readFileSync(statePath, 'utf-8')
const tablePath = resolve(process.cwd(), 'src/components/schema/TableMetadataSurface.vue')
const tableSource = readFileSync(tablePath, 'utf-8')

test('schema editor supports inline alias editing and persists normalized aliases', () => {
  assert.equal(tableSource.includes("import { normalizeAliasList } from '../../composables/useSchemaHubState'"), true)
  assert.equal(stateSource.includes('export function normalizeAliasList(value: unknown): string[] {'), true)
  assert.equal(tableSource.includes("startEdit(column, 'aliases')"), true)
  assert.equal(tableSource.includes('normalizeAliasList(active.value)'), true)
  assert.equal(source.includes('aliases: column.aliases || []'), true)
})

test('schema editor loads all workspace dataset schemas without auto-regenerating them', () => {
  assert.match(source, /const datasetResponse(?:: any)? = await workspaceApi\.listDatasets\(workspaceId\)/)
  assert.equal(source.includes('return await workspaceApi.getDatasetSchema(workspaceId, dataset.table_name)'), true)
  assert.equal(source.includes('await fetchWorkspaceSchema()'), true)
  assert.equal(source.includes('normalizeSchemaTables(datasets, schemas)'), true)
  assert.equal(source.includes('@regenerate="regenerateTableSchema"'), true)
})
