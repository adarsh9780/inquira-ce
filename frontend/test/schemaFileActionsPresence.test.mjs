import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('connection data has no legacy schema-file state and context follows the active workspace', () => {
  const appStorePath = resolve(process.cwd(), 'src/stores/appStore.js')
  const source = [
    readFileSync(appStorePath, 'utf-8'),
    readFileSync(resolve(process.cwd(), 'src/stores/workspaceStore.ts'), 'utf-8'),
  ].join('\n')

  assert.equal(source.includes('schemaFileId'), false)
  assert.equal(source.includes('isSchemaFileUploaded'), false)
  assert.equal(source.includes('const schemaContext = computed(() => {'), true)
  assert.equal(source.includes("return String(summary.schema_context || '')"), true)
  assert.equal(source.includes("return String(workspace?.schema_context || '')"), true)
  assert.equal(source.includes('openDataConnectionFlow,'), true)
  assert.equal(source.includes('fetchColumnCatalog,'), true)
})
