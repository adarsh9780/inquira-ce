import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
const source = readFileSync(schemaPath, 'utf-8')

function getFunctionBody(functionName, nextFunctionName) {
  const start = source.indexOf(`function ${functionName}`)
  const end = nextFunctionName ? source.indexOf(`function ${nextFunctionName}`, start) : source.length
  assert.notEqual(start, -1, `${functionName} should exist`)
  assert.notEqual(end, -1, `${nextFunctionName} should exist after ${functionName}`)
  return source.slice(start, end)
}

function getAsyncFunctionBody(functionName, nextFunctionName) {
  const start = source.indexOf(`async function ${functionName}`)
  const end = nextFunctionName ? source.indexOf(`async function ${nextFunctionName}`, start) : source.length
  assert.notEqual(start, -1, `${functionName} should exist`)
  assert.notEqual(end, -1, `${nextFunctionName} should exist after ${functionName}`)
  return source.slice(start, end)
}

test('schema editor supports alias editing and persists normalized aliases on save/export', () => {
  const saveDialogBody = getFunctionBody('saveEditDialog()', 'normalizeSchemaColumns(columns)')
  const saveSchemaBody = getAsyncFunctionBody('saveSchema()', 'refreshSchema()')

  assert.equal(source.includes('function normalizeAliasList(value) {'), true)
  assert.equal(source.includes('function updateSchemaAliases(index, aliasText) {'), true)
  assert.equal(source.includes('function formatAliasesForInput(value) {'), true)
  assert.equal(source.includes("@click=\"openEditDialog(i, 'aliases')\""), true)
  assert.equal(source.includes('title="Edit aliases"'), true)
  assert.equal(saveDialogBody.includes("field === 'aliases'"), true)
  assert.equal(saveDialogBody.includes('updateSchemaAliases(index, value)'), true)
  assert.equal(saveSchemaBody.includes('columns: normalizeSchemaColumns(schema.value)'), true)
})

test('schema editor keeps catalog datasets visible and does not auto-regenerate on dataset switch', () => {
  const handleDatasetSelectionBody = getAsyncFunctionBody('handleDatasetSelection(value)', 'handleDatasetSwitch(event)')
  const regenerateSchemaBody = getAsyncFunctionBody('regenerateSchema()', 'regenerateSchemaForPath(dataPath, tableName = null, options = {})')

  assert.equal(source.includes('normalizeDatasetEntries(catalogItems).forEach((item) => {'), true)
  assert.equal(source.includes('Schema has no columns yet. Click Regenerate to create descriptions manually.'), true)
  assert.equal(source.includes('Schema is not available yet. Click Regenerate to create it manually.'), true)
  assert.equal(handleDatasetSelectionBody.includes('await fetchSchemaData()'), true)
  assert.equal(handleDatasetSelectionBody.includes('regenerateSchemaForPath'), false)
  assert.equal(regenerateSchemaBody.includes('await regenerateSchemaForPath(dataPath, tableName)'), true)
})
