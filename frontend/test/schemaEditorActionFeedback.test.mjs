import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('schema editor actions emit feedback and keep refresh/regenerate/export flows wired', () => {
  const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaPath, 'utf-8')

  assert.equal(source.includes("import { toast } from '../../composables/useToast'"), true)
  assert.equal(source.includes("toast.success('Schema saved'"), true)
  assert.equal(source.includes("toast.success('Schema refreshed'"), true)
  assert.equal(source.includes("toast.success('Schema regenerated'"), true)
  assert.equal(source.includes("toast.success('Schema exported'"), true)
  assert.equal(source.includes('persistExportJsonFile'), true)
  assert.equal(source.includes("await import('@tauri-apps/plugin-dialog')"), true)
  assert.equal(source.includes('window.showSaveFilePicker'), true)
  assert.equal(source.includes("toast.info('Schema cache cleared'"), true)
  assert.equal(source.includes('async function refreshSchema()'), true)
  assert.equal(source.includes('const ok = await fetchSchemaData(true)'), true)
  assert.equal(source.includes('const ok = await regenerateSchemaForPath(dataPath, tableName)'), true)
  assert.equal(source.includes('const filename = `${selectedDatasetTable.value || \'schema\'}.json`'), true)
})
