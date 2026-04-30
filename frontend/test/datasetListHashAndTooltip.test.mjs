import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

test('dataset list strips hash suffixes from display names and uses full-path title on row root', () => {
  const source = readFileSync(resolve(process.cwd(), 'src/components/layout/UnifiedSidebar.vue'), 'utf-8')

  assert.equal(source.includes('const hashSegmentIndex = raw.search(/_[0-9a-f]{6,}(?=_|$)/i)'), true)
  assert.equal(source.includes('const withoutHashSuffix = hashSegmentIndex >= 0 ? raw.slice(0, hashSegmentIndex) : raw'), true)
  assert.equal(source.includes("const firstToken = raw.split('_')[0]?.trim()"), true)
  assert.equal(source.includes('function datasetRowTitle(dataset) {'), true)
  assert.equal(source.includes("const fullPath = String(dataset?.file_path || '').trim()"), true)
  assert.equal(source.includes('const sourceName = datasetSourceCaption(ds?.file_path).toLowerCase()'), true)
  assert.equal(source.includes(':title="datasetRowTitle(ds)"'), false)
  assert.equal(source.includes(':title="ds.table_name"'), false)
})
