import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('schema editor follows shared UI language and supports dataset dropdown, descriptions, and aliases', () => {
  const schemaPath = resolve(process.cwd(), 'src/components/preview/SchemaEditorTab.vue')
  const source = readFileSync(schemaPath, 'utf-8')

  assert.equal(source.includes('<HeaderDropdown'), true)
  assert.equal(source.includes('v-model="selectedDatasetTable"'), true)
  assert.equal(source.includes('placeholder="Select dataset"'), true)
  assert.equal(source.includes('@update:model-value="handleDatasetSelection"'), true)
  assert.equal(source.includes("@click=\"openEditDialog(-1, 'context')\""), true)
  assert.equal(source.includes("@click=\"openEditDialog(i, 'description')\""), true)
  assert.equal(source.includes("@click=\"openEditDialog(i, 'aliases')\""), true)
  assert.equal(source.includes("editDialog.field === 'description'"), true)
  assert.equal(source.includes("editDialog.field === 'aliases'"), true)
  assert.equal(source.includes("editDialog.field === 'context'"), true)
  assert.equal(source.includes('@click="saveEditDialog"'), true)
  assert.equal(source.includes('Save Changes'), true)
})
