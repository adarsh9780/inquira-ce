import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset list strips hash suffixes and keeps row titles in the legacy dataset surface', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/sidebar/SidebarDatasets.vue'), 'utf-8')

  assert.equal(source.includes("const withoutHashSuffix = raw.replace(/__\\d{6,}(?=__|$)/g, '')"), true)
  assert.equal(source.includes("const compacted = withoutHashSuffix.replace(/_{2,}/g, '_').replace(/^_+|_+$/g, '')"), true)
  assert.equal(source.includes('function datasetFriendlyName(tableName) {'), true)
  assert.equal(source.includes(':title="ds.table_name"'), true)
})
