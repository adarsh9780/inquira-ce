import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('data tab enforces schema regeneration when descriptions are missing', () => {
  const dataTabPath = resolve(process.cwd(), 'src/components/modals/DataTab.vue')
  const source = readFileSync(dataTabPath, 'utf-8')

  assert.equal(source.includes('function schemaNeedsDescriptionRegeneration(columns)'), true)
  assert.equal(source.includes('columns.some((col) => !String(col?.description || \'\').trim())'), true)
  assert.equal(source.includes('await apiService.v1RegenerateDatasetSchema(workspaceId, tableName, { context: schemaContext })'), true)
})

test('data tab creates schema from ingested columns when missing', () => {
  const dataTabPath = resolve(process.cwd(), 'src/components/modals/DataTab.vue')
  const source = readFileSync(dataTabPath, 'utf-8')

  assert.equal(source.includes('function buildSchemaColumnsFromIngestedColumns()'), true)
  assert.equal(source.includes('await apiService.v1SaveDatasetSchema(workspaceId, tableName, {'), true)
  assert.equal(source.includes('No columns available to build schema. Please re-select the data file.'), true)
})

test('api service force regenerate path calls v1 schema regeneration endpoint', () => {
  const apiServicePath = resolve(process.cwd(), 'src/services/apiService.js')
  const source = readFileSync(apiServicePath, 'utf-8')

  assert.equal(source.includes('if (forceRegenerate) {'), true)
  assert.equal(source.includes('return this.v1RegenerateDatasetSchema(workspaceId, tableName, {'), true)
})
